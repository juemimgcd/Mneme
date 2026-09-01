"""Load the configured embedding model once and generate normalized vectors off the event loop.

Dimension checks fail fast before incompatible vectors reach pgvector storage.
"""

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Any

from pgvector import SparseVector

from app.mneme.memoria.server.config import settings

SPARSE_HEAD_FILE = "sparse_linear.pt"
SPARSE_MAX_NONZERO = 1000


@lru_cache(maxsize=1)
def _embedding_model() -> Any:
    from sentence_transformers import SentenceTransformer

    cache_dir = Path(settings.EMBEDDING_CACHE_DIR).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_source = settings.EMBEDDING_MODEL_PATH.strip() or settings.EMBEDDING_MODEL_NAME.strip()
    if not model_source:
        raise RuntimeError("embedding model path or name must be configured")
    return SentenceTransformer(
        model_source,
        cache_folder=str(cache_dir),
        local_files_only=settings.EMBEDDING_LOCAL_FILES_ONLY,
    )


def embedding_model_ready() -> bool:
    return _embedding_model.cache_info().currsize > 0


def sparse_embeddings_enabled() -> bool:
    return settings.EMBEDDING_SPARSE_ENABLED


@lru_cache(maxsize=1)
def _sparse_head() -> Any:
    import torch
    from huggingface_hub import hf_hub_download

    configured = Path(settings.EMBEDDING_SPARSE_HEAD_PATH).expanduser()
    model_source = settings.EMBEDDING_MODEL_PATH.strip() or settings.EMBEDDING_MODEL_NAME.strip()
    bundled = Path(model_source).expanduser() / SPARSE_HEAD_FILE
    if settings.EMBEDDING_SPARSE_HEAD_PATH:
        if not configured.is_file():
            raise FileNotFoundError(f"configured sparse embedding head does not exist: {configured}")
        head_path = configured
    elif bundled.is_file():
        head_path = bundled
    else:
        head_path = Path(
            hf_hub_download(
                repo_id=settings.EMBEDDING_MODEL_NAME,
                filename=SPARSE_HEAD_FILE,
                cache_dir=str(Path(settings.EMBEDDING_CACHE_DIR).expanduser()),
                local_files_only=settings.EMBEDDING_LOCAL_FILES_ONLY,
            )
        )

    state = torch.load(head_path, map_location="cpu", weights_only=True)
    weight = state.get("weight")
    if weight is None or weight.ndim != 2 or weight.shape[0] != 1:
        raise RuntimeError(f"invalid sparse embedding head: {head_path}")
    head = torch.nn.Linear(int(weight.shape[1]), 1)
    head.load_state_dict(state)
    return head.eval()


def memory_embedding_text(*, subject: str, predicate: str, value: str) -> str:
    return "\n".join((subject.strip(), predicate.strip(), value.strip()))


def document_embedding_text(*, file_name: str, section_path: list[str], content: str) -> str:
    return "\n".join(
        part
        for part in (file_name.strip(), " > ".join(section_path).strip(), content.strip())
        if part
    )


def preload_embedding_model_sync() -> None:
    _embedding_model()
    if sparse_embeddings_enabled():
        _sparse_head()


async def preload_embedding_model() -> None:
    await asyncio.to_thread(preload_embedding_model_sync)


def _embed_texts_sync(texts: list[str]) -> list[list[float]]:
    vectors = _embedding_model().encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    result = vectors.tolist()
    if len(result) != len(texts):
        raise RuntimeError("embedding model returned an unexpected vector count")
    if any(len(vector) != settings.EMBEDDING_DIMENSION for vector in result):
        raise RuntimeError(
            f"embedding model must return {settings.EMBEDDING_DIMENSION}-dimension vectors"
        )
    return result


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Encode texts into normalized vectors without blocking the async event loop.

    The result count and configured dimension are validated before vectors
    are returned to projection or retrieval code.
    """
    if not texts:
        return []
    return await asyncio.to_thread(_embed_texts_sync, texts)


def _embed_texts_with_sparse_sync(texts: list[str]) -> tuple[list[list[float]], list[SparseVector]]:
    import torch

    model = _embedding_model()
    outputs = model.encode(
        texts,
        output_value=None,
        convert_to_numpy=False,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    tokenizer = model.tokenizer
    if tokenizer.vocab_size != settings.EMBEDDING_SPARSE_DIMENSION:
        raise RuntimeError(
            "embedding tokenizer vocabulary does not match EMBEDDING_SPARSE_DIMENSION"
        )
    head = _sparse_head().to(outputs[0]["token_embeddings"].device)
    ignored_token_ids = {
        tokenizer.cls_token_id,
        tokenizer.eos_token_id,
        tokenizer.pad_token_id,
        tokenizer.unk_token_id,
    }
    dense_vectors: list[list[float]] = []
    sparse_vectors: list[SparseVector] = []
    with torch.inference_mode():
        for output in outputs:
            dense = output["sentence_embedding"].detach().cpu().tolist()
            if len(dense) != settings.EMBEDDING_DIMENSION:
                raise RuntimeError(
                    f"embedding model must return {settings.EMBEDDING_DIMENSION}-dimension vectors"
                )
            token_ids = output["input_ids"].detach().cpu().tolist()
            token_embeddings = output["token_embeddings"]
            token_weights = torch.relu(head(token_embeddings)).squeeze(-1).detach().cpu().tolist()
            lexical_weights: dict[int, float] = {}
            for token_id, weight in zip(token_ids, token_weights, strict=True):
                if token_id in ignored_token_ids or weight <= lexical_weights.get(token_id, 0.0):
                    continue
                lexical_weights[token_id] = float(weight)
            if len(lexical_weights) > SPARSE_MAX_NONZERO:
                # ponytail: pgvector sparsevec caps nonzero entries; keep the strongest model weights.
                lexical_weights = dict(
                    sorted(lexical_weights.items(), key=lambda item: item[1], reverse=True)[
                        :SPARSE_MAX_NONZERO
                    ]
                )
            dense_vectors.append(dense)
            sparse_vectors.append(SparseVector(lexical_weights, settings.EMBEDDING_SPARSE_DIMENSION))
    if len(dense_vectors) != len(texts):
        raise RuntimeError("embedding model returned an unexpected vector count")
    return dense_vectors, sparse_vectors


async def embed_texts_with_sparse(
    texts: list[str],
) -> tuple[list[list[float]], list[SparseVector | None]]:
    if not texts:
        return [], []
    if not sparse_embeddings_enabled():
        dense = await embed_texts(texts)
        return dense, [None] * len(dense)
    return await asyncio.to_thread(_embed_texts_with_sparse_sync, texts)
