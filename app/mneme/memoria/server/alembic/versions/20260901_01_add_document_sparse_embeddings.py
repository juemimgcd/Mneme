"""add BGE-M3 sparse embeddings to document chunks

Revision ID: 20260901_01
Revises: 20260831_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import SPARSEVEC

from alembic import op
from app.mneme.memoria.server.config import settings

revision: str = "20260901_01"
down_revision: str | Sequence[str] | None = "20260831_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column(
            "sparse_embedding",
            SPARSEVEC(settings.EMBEDDING_SPARSE_DIMENSION),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_document_chunks_sparse_embedding_hnsw",
        "document_chunks",
        ["sparse_embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"sparse_embedding": "sparsevec_ip_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_sparse_embedding_hnsw", table_name="document_chunks")
    op.drop_column("document_chunks", "sparse_embedding")
