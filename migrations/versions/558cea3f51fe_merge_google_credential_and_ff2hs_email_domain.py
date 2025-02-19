"""merge google credential and ff2hs email domain

Revision ID: 558cea3f51fe
Revises: 275cf7fc677b, f20d6ec2c228
Create Date: 2025-02-19 00:04:33.707463

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '558cea3f51fe'
down_revision = ('275cf7fc677b', 'f20d6ec2c228')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
