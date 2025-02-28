"""Add is_default to google_credentials

Revision ID: 8d93f25a9b4c
Revises: <previous_revision_id>
Create Date: 2024-07-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d93f25a9b4c'
down_revision = '<previous_revision_id>'  # Replace with actual previous revision ID
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('google_credential', sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False))
    

def downgrade():
    op.drop_column('google_credential', 'is_default')