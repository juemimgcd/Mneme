"""Backfill Memoria memory and active-document embeddings."""

import argparse
import asyncio
import json

from sqlalchemy import func, select, update

from app.mneme.memoria.server.database import engine, open_read_session, open_write_session
from app.mneme.memoria.server.models.document_chunk import DocumentChunk
from app.mneme.memoria.server.models.document_projection import DocumentProjection
from app.mneme.memoria.server.models.memory_revision import MemoryRevision
from app.mneme.memoria.server.services.embeddings import (
    document_embedding_text,
    embed_texts,
    memory_embedding_text,
)


def _memory_filters(args: argparse.Namespace) -> list:
    filters = [MemoryRevision.embedding.is_(None)]
    if args.owner_id is not None:
        filters.append(MemoryRevision.owner_id == args.owner_id)
    if args.knowledge_base_id is not None:
        filters.append(MemoryRevision.knowledge_base_id == args.knowledge_base_id)
    return filters


async def memory_embedding_backfill(args: argparse.Namespace) -> dict:
    filters = _memory_filters(args)
    if args.resume_from:
        filters.append(MemoryRevision.revision_id > args.resume_from)
    if args.dry_run:
        async with open_read_session() as db:
            pending = await db.scalar(select(func.count()).select_from(MemoryRevision).where(*filters))
        return {"pending": int(pending or 0), "updated": 0, "dry_run": True}

    updated = 0
    resume_from = args.resume_from
    while True:
        statement = select(
            MemoryRevision.revision_id,
            MemoryRevision.subject,
            MemoryRevision.predicate,
            MemoryRevision.value,
        ).where(*filters)
        if resume_from:
            statement = statement.where(MemoryRevision.revision_id > resume_from)
        statement = statement.order_by(MemoryRevision.revision_id).limit(args.batch_size)
        async with open_read_session() as db:
            rows = (await db.execute(statement)).all()
        if not rows:
            break

        vectors = await embed_texts(
            [memory_embedding_text(subject=row.subject, predicate=row.predicate, value=row.value) for row in rows]
        )
        async with open_write_session() as db:
            for row, vector in zip(rows, vectors, strict=True):
                result = await db.execute(
                    update(MemoryRevision)
                    .where(
                        MemoryRevision.revision_id == row.revision_id,
                        MemoryRevision.embedding.is_(None),
                    )
                    .values(embedding=vector)
                )
                updated += result.rowcount or 0
        resume_from = rows[-1].revision_id

    return {"pending": 0, "updated": updated, "resume_from": resume_from, "dry_run": False}


def _document_filters(args: argparse.Namespace) -> list:
    filters = [DocumentChunk.is_active.is_(True), DocumentProjection.status == "active"]
    if args.owner_id is not None:
        filters.append(DocumentChunk.owner_id == args.owner_id)
    if args.knowledge_base_id is not None:
        filters.append(DocumentChunk.knowledge_base_id == args.knowledge_base_id)
    return filters


async def document_embedding_backfill(args: argparse.Namespace) -> dict:
    cursor = int(args.resume_from or 0)
    filters = _document_filters(args)
    if args.dry_run:
        async with open_read_session() as db:
            eligible = await db.scalar(
                select(func.count())
                .select_from(DocumentChunk)
                .join(DocumentProjection)
                .where(*filters, DocumentChunk.id > cursor)
            )
        return {"eligible": int(eligible or 0), "updated": 0, "dry_run": True}

    updated = 0
    # ponytail: embedding version is not persisted; reruns rewrite active vectors.
    # Add a version column only if representation upgrades become frequent.
    while True:
        statement = (
            select(
                DocumentChunk.id,
                DocumentChunk.content,
                DocumentChunk.section_path,
                DocumentProjection.file_name,
            )
            .join(DocumentProjection)
            .where(*filters, DocumentChunk.id > cursor)
            .order_by(DocumentChunk.id)
            .limit(args.batch_size)
        )
        async with open_read_session() as db:
            rows = (await db.execute(statement)).all()
        if not rows:
            break

        vectors = await embed_texts(
            [
                document_embedding_text(
                    file_name=row.file_name,
                    section_path=row.section_path,
                    content=row.content,
                )
                for row in rows
            ]
        )
        async with open_write_session() as db:
            for row, vector in zip(rows, vectors, strict=True):
                result = await db.execute(
                    update(DocumentChunk)
                    .where(DocumentChunk.id == row.id, DocumentChunk.is_active.is_(True))
                    .values(embedding=vector)
                )
                updated += result.rowcount or 0
        cursor = rows[-1].id

    return {"updated": updated, "resume_from": cursor, "dry_run": False}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--memory", action="store_true")
    mode.add_argument("--documents", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--owner-id", type=int)
    parser.add_argument("--knowledge-base-id")
    parser.add_argument("--resume-from")
    parser.add_argument("--batch-size", type=int, default=100)
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be positive")
    if args.owner_id is not None and args.owner_id <= 0:
        raise SystemExit("--owner-id must be positive")
    if args.documents and args.resume_from:
        try:
            resume_from = int(args.resume_from)
        except ValueError as exc:
            raise SystemExit("--resume-from must be a numeric chunk row ID") from exc
        if resume_from < 0:
            raise SystemExit("--resume-from must be non-negative")
    try:
        report = await document_embedding_backfill(args) if args.documents else await memory_embedding_backfill(args)
        print(json.dumps(report, sort_keys=True))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
