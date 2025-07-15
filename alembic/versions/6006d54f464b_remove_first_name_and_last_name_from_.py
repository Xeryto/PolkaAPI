"""Remove first_name and last_name from users table

Revision ID: 6006d54f464b
Revises: 6469a48c7c0c
Create Date: 2025-07-12 00:56:47.478471

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6006d54f464b'
down_revision = '6469a48c7c0c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 