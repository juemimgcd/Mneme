"""Run a reproducible BEIR SciFact retrieval benchmark.

The benchmark compares the configured dense embedding model with a lightweight
lexical baseline, reciprocal-rank fusion, and an optional configured reranker.
It downloads the official BEIR archive linked by the Hugging Face dataset card.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import subprocess
import sys
import time
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any
from urllib.request import urlopen

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.mneme.clients.embedding_client import get_embeddings, resolve_embedding_source
from app.mneme.clients.reranker_client import get_reranker
from app.mneme.conf.config import settings
from app.mneme.domains.eval.service import (
    calculate_mrr,
    calculate_ndcg,
    calculate_recall_at_k,
)
from app.mneme.memoria.server.retrieval.contracts import DocumentSearchHit
from app.mneme.memoria.server.retrieval.fusion import (
    DENSE_SCORE_WEIGHT,
    FUSION_CANDIDATE_K,
    LEXICAL_RRF_WEIGHT,
    RRF_CONSTANT,
    normalized_score_fusion,
)

DATASET_NAME = "BEIR SciFact"
DATASET_URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip"
DATASET_MD5 = "5f7d1de60b170fc8027bb7898e2efca1"
HF_DATASET_CARD = "https://huggingface.co/datasets/BeIR/scifact"
HF_DATASET_REVISION = "b3b5335604bf5ee3c4447671af975ea25143d4f5"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="JSON report path")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("storage/eval/beir"),
        help="download and extraction cache",
    )
    parser.add_argument("--sample-size", type=int, default=100, help="test queries to evaluate")
    parser.add_argument(
        "--corpus-size",
        type=int,
        default=1000,
        help="sampled corpus size; all selected-query positives are always retained",
    )
    parser.add_argument("--seed", type=int, default=20260830, help="deterministic query sample seed")
    parser.add_argument("--top-k", type=int, default=10, help="metric cutoff")
    parser.add_argument("--candidate-k", type=int, default=50, help="dense/lexical candidates for RRF")
    parser.add_argument("--rerank-k", type=int, default=20, help="hybrid candidates sent to reranker")
    parser.add_argument("--embedding-batch-size", type=int, default=32)
    parser.add_argument("--reranker-batch-size", type=int, default=16)
    parser.add_argument("--reranker", action="store_true", help="run the configured CrossEncoder")
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    for name in (
        "sample_size",
        "corpus_size",
        "top_k",
        "candidate_k",
        "rerank_k",
        "embedding_batch_size",
        "reranker_batch_size",
    ):
        if getattr(args, name) < 1:
            raise ValueError(f"--{name.replace('_', '-')} must be positive")
    if args.candidate_k < args.top_k:
        raise ValueError("--candidate-k must be at least --top-k")
    if args.rerank_k > args.candidate_k:
        raise ValueError("--rerank-k cannot exceed --candidate-k")


def _digest(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _download_dataset(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    archive = data_dir / "scifact.zip"
    dataset_dir = data_dir / "scifact"
    if not archive.exists() or _digest(archive, "md5") != DATASET_MD5:
        temporary = archive.with_suffix(".zip.part")
        with urlopen(DATASET_URL, timeout=120) as response, temporary.open("wb") as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
        if _digest(temporary, "md5") != DATASET_MD5:
            temporary.unlink(missing_ok=True)
            raise ValueError("downloaded SciFact archive failed the published MD5 check")
        os.replace(temporary, archive)

    required = (
        dataset_dir / "corpus.jsonl",
        dataset_dir / "queries.jsonl",
        dataset_dir / "qrels" / "test.tsv",
    )
    if not all(path.is_file() for path in required):
        extraction_root = data_dir.resolve()
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                destination = (data_dir / member.filename).resolve()
                if not destination.is_relative_to(extraction_root):
                    raise ValueError(f"unsafe archive member: {member.filename}")
            bundle.extractall(data_dir)
    if not all(path.is_file() for path in required):
        raise FileNotFoundError("SciFact archive is missing corpus, queries, or test qrels")
    return dataset_dir


def _load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        row_id = str(row.get("_id", "")).strip()
        if not row_id or row_id in rows:
            raise ValueError(f"invalid or duplicate _id at {path}:{line_number}")
        rows[row_id] = row
    return rows


def _load_qrels(path: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source, delimiter="\t"):
            if int(row["score"]) > 0:
                result[str(row["query-id"])].add(str(row["corpus-id"]))
    return dict(result)


def _document_text(row: dict[str, Any]) -> str:
    return "\n".join(part.strip() for part in (str(row.get("title", "")), str(row.get("text", ""))) if part.strip())


def _model_identity(model_source: str) -> str:
    path = Path(model_source)
    if not path.exists():
        return model_source
    resolved = path.resolve()
    digest = hashlib.sha256(str(resolved).encode())
    for file_path in sorted(path for path in resolved.rglob("*") if path.is_file()):
        stat = file_path.stat()
        digest.update(str(file_path.relative_to(resolved)).encode())
        digest.update(f"\0{stat.st_size}\0{stat.st_mtime_ns}\0".encode())
    return digest.hexdigest()


def _embedding_cache_path(data_dir: Path, model_identity: str) -> Path:
    key = hashlib.sha256(f"v2\0{DATASET_MD5}\0{model_identity}".encode()).hexdigest()[:12]
    return data_dir / f"scifact-embeddings-{key}.npz"


def _document_vectors(
    embeddings: Any,
    doc_ids: list[str],
    doc_texts: list[str],
    cache_path: Path,
) -> tuple[np.ndarray, int, int]:
    text_hashes = [hashlib.sha256(text.encode()).hexdigest() for text in doc_texts]
    cached: dict[str, tuple[str, np.ndarray]] = {}
    if cache_path.is_file():
        with np.load(cache_path, allow_pickle=False) as cache:
            if {"doc_ids", "text_hashes", "vectors"}.difference(cache.files):
                raise ValueError(f"invalid embedding cache: {cache_path}")
            cached_ids = np.asarray(cache["doc_ids"], dtype=str).tolist()
            cached_hashes = np.asarray(cache["text_hashes"], dtype=str).tolist()
            cached_vectors = np.asarray(cache["vectors"], dtype=np.float32)
        if (
            cached_vectors.ndim != 2
            or len(cached_ids) != len(cached_vectors)
            or len(cached_hashes) != len(cached_vectors)
            or len(set(cached_ids)) != len(cached_ids)
        ):
            raise ValueError(f"invalid embedding cache: {cache_path}")
        cached = dict(zip(cached_ids, zip(cached_hashes, cached_vectors, strict=True), strict=True))

    missing_indexes = [
        index
        for index, (doc_id, text_hash) in enumerate(zip(doc_ids, text_hashes, strict=True))
        if doc_id not in cached or cached[doc_id][0] != text_hash
    ]
    if missing_indexes:
        missing_vectors = np.asarray(
            embeddings.embed_documents([doc_texts[index] for index in missing_indexes]),
            dtype=np.float32,
        )
        if missing_vectors.ndim != 2 or len(missing_vectors) != len(missing_indexes):
            raise ValueError("embedding model returned an unexpected document vector shape")
        if cached and missing_vectors.shape[1] != len(next(iter(cached.values()))[1]):
            raise ValueError(f"embedding dimensions do not match cache: {cache_path}")
        cached.update(
            (doc_ids[index], (text_hashes[index], vector))
            for index, vector in zip(missing_indexes, missing_vectors, strict=True)
        )
        temporary = cache_path.with_suffix(".npz.part")
        with temporary.open("wb") as target:
            np.savez_compressed(
                target,
                doc_ids=np.asarray(list(cached)),
                text_hashes=np.asarray([item[0] for item in cached.values()]),
                vectors=np.asarray([item[1] for item in cached.values()], dtype=np.float32),
            )
        os.replace(temporary, cache_path)

    return (
        np.stack([cached[doc_id][1] for doc_id in doc_ids]),
        len(doc_ids) - len(missing_indexes),
        len(missing_indexes),
    )


def _top_ids(scores: np.ndarray, doc_ids: list[str], limit: int) -> list[str]:
    limit = min(limit, len(doc_ids))
    candidates = np.argpartition(-scores, limit - 1)[:limit]
    ranked = candidates[np.argsort(-scores[candidates], kind="stable")]
    return [doc_ids[index] for index in ranked]


def _rrf(
    left: list[str],
    right: list[str],
    limit: int,
    *,
    left_weight: float = 1.0,
    right_weight: float = 1.0,
) -> list[str]:
    scores: dict[str, float] = defaultdict(float)
    for ranking, weight in ((left, left_weight), (right, right_weight)):
        for rank, doc_id in enumerate(ranking, 1):
            scores[doc_id] += weight / (RRF_CONSTANT + rank)
    return sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))[:limit]


def _metrics(rankings: dict[str, list[str]], qrels: dict[str, set[str]], top_k: int) -> dict[str, float]:
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    ndcgs: list[float] = []
    for query_id, ranking in rankings.items():
        expected = sorted(qrels[query_id])
        retrieved = ranking[:top_k]
        recalls.append(calculate_recall_at_k(expected_ids=expected, retrieved_ids=retrieved))
        reciprocal_ranks.append(calculate_mrr(expected_ids=expected, retrieved_ids=retrieved))
        ndcgs.append(calculate_ndcg(expected_ids=expected, retrieved_ids=retrieved))
    return {
        f"recall@{top_k}": round(fmean(recalls), 6),
        f"mrr@{top_k}": round(fmean(reciprocal_ranks), 6),
        f"ndcg@{top_k}": round(fmean(ndcgs), 6),
    }


def _failures(
    rankings: dict[str, list[str]],
    qrels: dict[str, set[str]],
    queries: dict[str, dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    failures = []
    for query_id, ranking in rankings.items():
        expected = qrels[query_id]
        retrieved = ranking[:top_k]
        missing = sorted(expected.difference(retrieved))
        if missing:
            failures.append(
                {
                    "query_id": query_id,
                    "query": str(queries[query_id].get("text", "")),
                    "expected": sorted(expected),
                    "missing": missing,
                    "retrieved": retrieved,
                }
            )
    return failures[:20]


def _git_state() -> dict[str, Any]:
    environment_commit = os.getenv("BEIR_EVAL_GIT_COMMIT", "").strip()
    environment_dirty = os.getenv("BEIR_EVAL_GIT_DIRTY", "").strip().lower()
    if environment_commit:
        return {
            "commit": environment_commit,
            "dirty": environment_dirty == "true" if environment_dirty else None,
        }
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return {"commit": commit, "dirty": dirty}
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def run(args: argparse.Namespace) -> dict[str, Any]:
    _validate_args(args)
    dataset_dir = _download_dataset(args.data_dir)
    corpus = _load_jsonl(dataset_dir / "corpus.jsonl")
    queries = _load_jsonl(dataset_dir / "queries.jsonl")
    qrels = _load_qrels(dataset_dir / "qrels" / "test.tsv")
    eligible_query_ids = sorted(set(queries).intersection(qrels))
    if args.sample_size > len(eligible_query_ids):
        raise ValueError(f"--sample-size exceeds the {len(eligible_query_ids)} SciFact test queries")
    query_ids = sorted(random.Random(args.seed).sample(eligible_query_ids, args.sample_size))
    positive_doc_ids = sorted({doc_id for query_id in query_ids for doc_id in qrels[query_id]})
    if args.corpus_size < len(positive_doc_ids):
        raise ValueError(
            f"--corpus-size must retain all {len(positive_doc_ids)} positive documents for the sampled queries"
        )
    if args.corpus_size > len(corpus):
        raise ValueError(f"--corpus-size exceeds the {len(corpus)} SciFact documents")
    distractor_ids = sorted(set(corpus).difference(positive_doc_ids))
    sampled_distractors = random.Random(args.seed + 1).sample(
        distractor_ids,
        args.corpus_size - len(positive_doc_ids),
    )
    doc_ids = sorted([*positive_doc_ids, *sampled_distractors])
    doc_texts = [_document_text(corpus[doc_id]) for doc_id in doc_ids]
    query_texts = [str(queries[query_id].get("text", "")) for query_id in query_ids]
    timings: dict[str, float] = {}

    embedding_model = str(settings.EMBEDDING_MODEL_PATH or settings.EMBEDDING_MODEL_NAME)
    embeddings = get_embeddings()
    embedding_source, _ = resolve_embedding_source()
    embedding_cache = _embedding_cache_path(args.data_dir, _model_identity(embedding_source))
    embeddings.encode_kwargs["batch_size"] = args.embedding_batch_size
    started = time.perf_counter()
    doc_vectors, cache_hits, encoded_count = _document_vectors(
        embeddings,
        doc_ids,
        doc_texts,
        embedding_cache,
    )
    timings["dense_corpus_encode_seconds"] = round(time.perf_counter() - started, 3)
    timings["dense_corpus_cache_hits"] = cache_hits
    timings["dense_corpus_encoded_count"] = encoded_count
    started = time.perf_counter()
    query_vectors = np.asarray(
        embeddings.embed_documents(query_texts),
        dtype=np.float32,
    )
    timings["dense_query_encode_seconds"] = round(time.perf_counter() - started, 3)
    started = time.perf_counter()
    dense_scores = query_vectors @ doc_vectors.T
    dense = {
        query_id: _top_ids(dense_scores[index], doc_ids, args.candidate_k) for index, query_id in enumerate(query_ids)
    }
    timings["dense_search_seconds"] = round(time.perf_counter() - started, 3)

    # ponytail: TF-IDF is an offline lexical proxy; use a live PostgreSQL run when backend parity matters.
    started = time.perf_counter()
    vectorizer = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2), min_df=2)
    lexical_corpus = vectorizer.fit_transform(doc_texts)
    lexical_queries = vectorizer.transform(query_texts)
    timings["lexical_fit_seconds"] = round(time.perf_counter() - started, 3)
    started = time.perf_counter()
    lexical_scores = (lexical_queries @ lexical_corpus.T).toarray()
    lexical = {
        query_id: _top_ids(lexical_scores[index], doc_ids, args.candidate_k)
        for index, query_id in enumerate(query_ids)
    }
    timings["lexical_search_seconds"] = round(time.perf_counter() - started, 3)
    started = time.perf_counter()
    hybrid = {query_id: _rrf(dense[query_id], lexical[query_id], args.candidate_k) for query_id in query_ids}
    weighted_hybrid = {
        query_id: _rrf(
            dense[query_id],
            lexical[query_id],
            args.candidate_k,
            right_weight=LEXICAL_RRF_WEIGHT,
        )
        for query_id in query_ids
    }
    timings["hybrid_rrf_seconds"] = round(time.perf_counter() - started, 3)
    started = time.perf_counter()
    doc_index = {doc_id: index for index, doc_id in enumerate(doc_ids)}
    score_fusion = {}
    for query_index, query_id in enumerate(query_ids):
        dense_hits = [
            DocumentSearchHit(
                doc_id,
                doc_id,
                doc_texts[doc_index[doc_id]],
                {},
                float(dense_scores[query_index, doc_index[doc_id]]),
            )
            for doc_id in dense[query_id]
        ]
        lexical_hits = [
            DocumentSearchHit(
                doc_id,
                doc_id,
                doc_texts[doc_index[doc_id]],
                {},
                float(lexical_scores[query_index, doc_index[doc_id]]),
            )
            for doc_id in lexical[query_id]
        ]
        score_fusion[query_id] = [
            item.evidence_id
            for item in normalized_score_fusion(
                (dense_hits, lexical_hits),
                top_k=args.candidate_k,
                weights=(DENSE_SCORE_WEIGHT, 1.0 - DENSE_SCORE_WEIGHT),
            )
        ]
    timings["score_fusion_seconds"] = round(time.perf_counter() - started, 3)

    rankings = {
        "dense": dense,
        "lexical_tfidf": lexical,
        "hybrid_rrf": hybrid,
        "dense_weighted_rrf": weighted_hybrid,
        "normalized_score_fusion": score_fusion,
    }
    reranker_model = None
    if args.reranker:
        reranker = get_reranker()
        if reranker is None:
            raise RuntimeError("--reranker requires RERANKER_ENABLED=true")
        reranker_model = settings.RERANKER_MODEL_PATH or settings.RERANKER_MODEL_NAME
        pairs: list[tuple[str, str]] = []
        candidates_by_pipeline: dict[str, dict[str, list[str]]] = {}
        doc_index = {doc_id: index for index, doc_id in enumerate(doc_ids)}
        for result_name, source in (
            ("dense_rerank", dense),
            ("hybrid_rerank", weighted_hybrid),
        ):
            candidates_by_query: dict[str, list[str]] = {}
            for query_id in query_ids:
                candidates = source[query_id][: args.rerank_k]
                candidates_by_query[query_id] = candidates
                pairs.extend((str(queries[query_id]["text"]), doc_texts[doc_index[doc_id]]) for doc_id in candidates)
            candidates_by_pipeline[result_name] = candidates_by_query
        started = time.perf_counter()
        scores = reranker.predict(
            pairs,
            batch_size=args.reranker_batch_size,
            show_progress_bar=True,
        )
        timings["rerank_seconds"] = round(time.perf_counter() - started, 3)
        timings["rerank_pair_count"] = len(pairs)
        offset = 0
        for result_name, candidates_by_query in candidates_by_pipeline.items():
            reranked: dict[str, list[str]] = {}
            for query_id in query_ids:
                candidates = candidates_by_query[query_id]
                query_scores = scores[offset : offset + len(candidates)]
                offset += len(candidates)
                reranked[query_id] = [
                    doc_id
                    for _, doc_id in sorted(
                        zip(query_scores, candidates, strict=True),
                        key=lambda item: -float(item[0]),
                    )
                ]
            rankings[result_name] = reranked

    metrics = {name: _metrics(items, qrels, args.top_k) for name, items in rankings.items()}
    return {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "repository": _git_state(),
        "dataset": {
            "name": DATASET_NAME,
            "download_url": DATASET_URL,
            "published_md5": DATASET_MD5,
            "archive_sha256": _digest(args.data_dir / "scifact.zip"),
            "hugging_face_card": HF_DATASET_CARD,
            "hugging_face_revision": HF_DATASET_REVISION,
            "full_corpus_count": len(corpus),
            "evaluated_corpus_count": len(doc_ids),
            "positive_document_count": len(positive_doc_ids),
            "corpus_sampling": "all selected-query qrel positives plus fixed-seed distractors",
            "test_query_count": len(eligible_query_ids),
            "evaluated_query_count": len(query_ids),
            "query_ids": query_ids,
            "sample_seed": args.seed,
        },
        "models": {
            "embedding": embedding_model,
            "embedding_source": embedding_source,
            "reranker": reranker_model,
            "lexical": "sklearn.TfidfVectorizer",
        },
        "configuration": {
            "top_k": args.top_k,
            "corpus_size": args.corpus_size,
            "candidate_k": args.candidate_k,
            "rerank_k": args.rerank_k if args.reranker else None,
            "embedding_batch_size": args.embedding_batch_size,
            "embedding_cache": str(embedding_cache),
            "reranker_batch_size": args.reranker_batch_size if args.reranker else None,
            "rrf_constant": RRF_CONSTANT,
            "production_candidate_k": FUSION_CANDIDATE_K,
            "dense_rrf_weight": 1.0,
            "lexical_rrf_weight": LEXICAL_RRF_WEIGHT,
            "dense_score_weight": DENSE_SCORE_WEIGHT,
        },
        "metrics": metrics,
        "timings": timings,
        "failure_samples": {name: _failures(items, qrels, queries, args.top_k) for name, items in rankings.items()},
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = run(args)
    except Exception as exc:
        print(f"BEIR evaluation failed: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": report["metrics"], "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
