"""fix postgres enum for interventionstatus

Revision ID: 7a4263c7f8f7
Revises: 49e65fab98aa
Create Date: 2026-05-13 19:23:21.710481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a4263c7f8f7'
down_revision: Union[str, Sequence[str], None] = '49e65fab98aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.engine.name == 'postgresql':
        # PostgreSQL requires explicit ALTER TYPE commands to add enum values.
        # We add 'PENDING_REVIEW' and 'FAILED' which were missing from the original enum.
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE interventionstatus ADD VALUE IF NOT EXISTS 'PENDING_REVIEW'")
            op.execute("ALTER TYPE interventionstatus ADD VALUE IF NOT EXISTS 'FAILED'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
