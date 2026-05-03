"""Merge multiple heads

Revision ID: f9ff11a14bee
Revises: be73fc250f7a
Create Date: 2026-05-03 16:04:41.396975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9ff11a14bee'
down_revision: Union[str, Sequence[str], None] = 'be73fc250f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
