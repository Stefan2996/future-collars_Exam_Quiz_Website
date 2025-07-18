"""Add image_url to QuizPack

Revision ID: bd75b74d44c0
Revises: aeaa8ecd02b0
Create Date: 2025-07-14 21:20:38.338451

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd75b74d44c0'
down_revision: Union[str, Sequence[str], None] = 'aeaa8ecd02b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('quiz_pack', sa.Column('image_url', sa.String(length=200), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('quiz_pack', 'image_url')
    # ### end Alembic commands ###
