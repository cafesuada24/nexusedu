"""Merge multiple heads

Revision ID: be73fc250f7a
Revises: 65576d03c79c, 94d2bd39c0a6
Create Date: 2026-05-03 16:04:09.796569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be73fc250f7a'
down_revision: Union[str, Sequence[str], None] = ('65576d03c79c', '94d2bd39c0a6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
