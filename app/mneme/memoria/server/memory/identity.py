"""Build stable normalized identities for memories, evidence records, and reconciliation lock slots.

Canonical hashes make retries idempotent without treating raw user text as an identifier.
"""

import hashlib
import json


def _canonical_identity(tag: str, values: list[str | int | None]) -> bytes:
    serialized = json.dumps(
        [tag, 1, values],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return serialized.encode("utf-8")


def normalize_memory_text(value: str) -> str:
    """Normalize memory text before hashing or comparing identity slots.

    Normalization is intentionally conservative so semantically different
    facts are not merged merely because they look similar.
    """
    return " ".join(value.strip().split()).casefold()


def memory_fingerprint(*, subject: str, predicate: str, value: str) -> str:
    """Return a stable content identity for one normalized subject-predicate-value fact.

    The fingerprint supports idempotent retries and compatible-memory lookup;
    it is not used as an authorization token.
    """
    normalized = "\x1f".join(
        (
            normalize_memory_text(subject),
            normalize_memory_text(predicate),
            normalize_memory_text(value),
        )
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def evidence_identity(
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    source_type: str,
    source_id: str,
    source_version: str,
    content_hash: str,
) -> str:
    """Build the idempotency identity for one scoped source-evidence version.

    Owner, knowledge base, source identity, source version, and content hash
    all participate so unrelated evidence cannot collide across scopes.
    """
    values: list[str | int | None] = [
        owner_id,
        knowledge_base_id,
        source_type,
        source_id,
        source_version,
        content_hash,
    ]
    identity = _canonical_identity("mneme:evidence-identity", values)
    return hashlib.sha256(identity).hexdigest()


def memory_slot_lock_key(
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    memory_type: str,
    subject: str,
    predicate: str,
) -> int:
    """Build a deterministic advisory-lock key for a logical memory slot.

    A slot is the owner/KB/type/subject/predicate location where competing
    values must be reconciled serially.
    """
    identity = _canonical_identity(
        "mneme:memory-slot-lock",
        [
            owner_id,
            knowledge_base_id,
            memory_type,
            subject,
            predicate,
        ],
    )
    return int.from_bytes(
        hashlib.sha256(identity).digest()[:8],
        byteorder="big",
        signed=True,
    )
