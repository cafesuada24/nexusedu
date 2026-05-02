"""empty message

Revision ID: 9f1ec9cbec66
Revises: b1c75aa208ce, bd0aa53c2057
Create Date: 2026-05-02 23:12:10.666935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f1ec9cbec66'
down_revision: Union[str, Sequence[str], None] = ('b1c75aa208ce', 'bd0aa53c2057')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
