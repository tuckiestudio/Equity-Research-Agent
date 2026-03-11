"""add llm routing preferences

Revision ID: 003_add_llm_routing
Revises: 002_add_openrouter_chutes
Create Date: 2026-02-24 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '003_add_llm_routing'
down_revision: Union[str, None] = '002_add_openrouter_chutes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add llm_routing_preferences column to user_settings."""
    op.add_column(
        'user_settings',
        sa.Column(
            'llm_routing_preferences',
            postgresql.JSONB(none_as_null=True),
            nullable=True
        )
    )
    print("Added llm_routing_preferences column to user_settings")


def downgrade() -> None:
    """Remove llm_routing_preferences column from user_settings."""
    op.drop_column('user_settings', 'llm_routing_preferences')
    print("Removed llm_routing_preferences column from user_settings")
