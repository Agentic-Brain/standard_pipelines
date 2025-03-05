"""added proper oauth token fields to ZohoCredentials

Revision ID: 5164608501b3
Revises: 45a7ba2d18ad
Create Date: 2025-03-04 14:08:58.398719

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5164608501b3'
down_revision = '45a7ba2d18ad'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('zoho_credential', schema=None) as batch_op:
        # Rename existing columns so that data is preserved.
        batch_op.alter_column('zoho_client_id',
                              new_column_name='oauth_client_id',
                              existing_type=sa.String(length=255))
        batch_op.alter_column('zoho_client_secret',
                              new_column_name='oauth_client_secret',
                              existing_type=sa.String(length=255))
        batch_op.alter_column('zoho_refresh_token',
                              new_column_name='oauth_refresh_token',
                              existing_type=sa.String(length=255))
        # Add new columns that did not exist before.
        batch_op.add_column(sa.Column('oauth_access_token', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('oauth_expires_at', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('zoho_credential', schema=None) as batch_op:
        # Remove the new columns.
        batch_op.drop_column('oauth_access_token')
        batch_op.drop_column('oauth_expires_at')
        # Rename the columns back to their original names.
        batch_op.alter_column('oauth_client_id',
                              new_column_name='zoho_client_id',
                              existing_type=sa.String(length=255))
        batch_op.alter_column('oauth_client_secret',
                              new_column_name='zoho_client_secret',
                              existing_type=sa.String(length=255))
        batch_op.alter_column('oauth_refresh_token',
                              new_column_name='zoho_refresh_token',
                              existing_type=sa.String(length=255))
