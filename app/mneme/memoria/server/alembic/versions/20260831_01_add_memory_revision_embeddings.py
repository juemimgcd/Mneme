"""add semantic embeddings to memory revisions

Revision ID: 20260831_01
Revises: 20260830_01
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op
from app.mneme.memoria.server.config import settings

revision: str = "20260831_01"
down_revision: str | Sequence[str] | None = "20260830_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memory_revisions",
        sa.Column("embedding", Vector(settings.EMBEDDING_DIMENSION), nullable=True),
    )
    op.create_index(
        "ix_memory_revisions_embedding_hnsw",
        "memory_revisions",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_memory_revisions_embedding_hnsw", table_name="memory_revisions")
    op.drop_column("memory_revisions", "embedding")
