"""add archive to portfolio_stocks

Revision ID: 0001_archive_stocks
Revises: 5434eda6045a
Create Date: 2026-02-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_archive_stocks'
down_revision: Union[str, None] = '5434eda6045a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add archived_at and is_archived columns to portfolio_stocks table
    op.add_column('portfolio_stocks', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('portfolio_stocks', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'))

    # Create index for efficient querying of archived stocks
    op.create_index('ix_portfolio_stocks_is_archived', 'portfolio_stocks', ['is_archived'])


def downgrade() -> None:
    op.drop_index('ix_portfolio_stocks_is_archived', 'portfolio_stocks')
    op.drop_column('portfolio_stocks', 'is_archived')
    op.drop_column('portfolio_stocks', 'archived_at')
