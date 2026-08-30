"""persist memory sensitivity and ad personalization consent

Revision ID: 20260830_01
Revises: 20260718_03
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_01"
down_revision: str | Sequence[str] | None = "20260718_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "canonical_memories",
        sa.Column("sensitivity", sa.String(length=16), server_default="unknown", nullable=False),
    )
    op.create_check_constraint(
        "ck_canonical_memories_sensitivity",
        "canonical_memories",
        "sensitivity IN ('unknown', 'low', 'sensitive')",
    )
    op.execute(
        """
        UPDATE canonical_memories AS memory
        SET sensitivity = 'sensitive'
        FROM (
            SELECT
                owner_id,
                knowledge_base_id,
                fingerprint
            FROM memory_candidates
            WHERE status = 'promoted'
              AND sensitivity = 'sensitive'
            GROUP BY owner_id, knowledge_base_id, fingerprint
        ) AS candidates
        WHERE memory.owner_id = candidates.owner_id
          AND memory.knowledge_base_id IS NOT DISTINCT FROM candidates.knowledge_base_id
          AND memory.fingerprint = candidates.fingerprint
        """
    )
    op.add_column(
        "memory_settings",
        sa.Column("ad_personalization_enabled", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "memory_settings",
        sa.Column("ad_personalization_last_event_occurred_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "memory_settings",
        sa.Column("ad_personalization_last_event_id", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("memory_settings", "ad_personalization_last_event_id")
    op.drop_column("memory_settings", "ad_personalization_last_event_occurred_at")
    op.drop_column("memory_settings", "ad_personalization_enabled")
    op.drop_constraint(
        "ck_canonical_memories_sensitivity",
        "canonical_memories",
        type_="check",
    )
    op.drop_column("canonical_memories", "sensitivity")
