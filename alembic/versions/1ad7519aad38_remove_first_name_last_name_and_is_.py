"""Remove first_name, last_name, and is_profile_complete from User model

Revision ID: 1ad7519aad38
Revises: 38af7d565584
Create Date: 2025-07-06 03:37:55.005015

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1ad7519aad38'
down_revision = '38af7d565584'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 