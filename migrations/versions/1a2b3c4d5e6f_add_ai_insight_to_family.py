"""Add ai_insight to family

Revision ID: 1a2b3c4d5e6f
Revises: 0386ab5f160f
Create Date: 2026-07-01 08:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = '0386ab5f160f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('families', sa.Column('ai_insight', sa.String(length=500), nullable=True))
    op.add_column('families', sa.Column('insight_generated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('families', 'insight_generated_at')
    op.drop_column('families', 'ai_insight')
