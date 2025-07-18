"""Migrate OAuth fields to new standardized structure

Revision ID: 4a90b922c1c5
Revises: aeeabd940510
Create Date: 2025-05-28 20:27:35.866496

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = '4a90b922c1c5'
down_revision = 'aeeabd940510'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('rapidapi_credential',
    sa.Column('rapidapi_key', sa.Text(), nullable=False),
    sa.Column('rapidapi_host', sa.Text(), nullable=False),
    sa.Column('client_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['client.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_id')
    )
    
    # Google credential migration - add new columns first
    with op.batch_alter_table('google_credential', schema=None) as batch_op:
        batch_op.add_column(sa.Column('oauth_refresh_token', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('oauth_access_token', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('oauth_token_expires_at', sa.Integer(), nullable=True))
    
    # Copy data from old column to new column
    google_table = table('google_credential',
        column('refresh_token', sa.String),
        column('oauth_refresh_token', sa.String)
    )
    op.execute(
        google_table.update().values(oauth_refresh_token=google_table.c.refresh_token)
    )
    
    # Make oauth_refresh_token NOT NULL after data is copied
    with op.batch_alter_table('google_credential', schema=None) as batch_op:
        batch_op.alter_column('oauth_refresh_token', nullable=False)
        batch_op.drop_column('refresh_token')

    # HubSpot credential migration - add new columns first
    with op.batch_alter_table('hubspot_credential', schema=None) as batch_op:
        batch_op.add_column(sa.Column('oauth_refresh_token', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('oauth_access_token', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('oauth_token_expires_at', sa.Integer(), nullable=True))
    
    # Copy data from old column to new column
    hubspot_table = table('hubspot_credential',
        column('hubspot_refresh_token', sa.String),
        column('oauth_refresh_token', sa.String)
    )
    op.execute(
        hubspot_table.update().values(oauth_refresh_token=hubspot_table.c.hubspot_refresh_token)
    )
    
    # Make oauth_refresh_token NOT NULL after data is copied
    with op.batch_alter_table('hubspot_credential', schema=None) as batch_op:
        batch_op.alter_column('oauth_refresh_token', nullable=False)
        batch_op.drop_column('hubspot_refresh_token')

    # Zoho credential migration - just add the new field (Zoho already has oauth_refresh_token and oauth_access_token)
    with op.batch_alter_table('zoho_credential', schema=None) as batch_op:
        batch_op.add_column(sa.Column('oauth_token_expires_at', sa.Integer(), nullable=True))
    
    # Copy expires_at data if needed
    zoho_table = table('zoho_credential',
        column('oauth_expires_at', sa.Integer),
        column('oauth_token_expires_at', sa.Integer)
    )
    op.execute(
        zoho_table.update().values(oauth_token_expires_at=zoho_table.c.oauth_expires_at)
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    
    # Zoho - just remove the new field
    with op.batch_alter_table('zoho_credential', schema=None) as batch_op:
        batch_op.drop_column('oauth_token_expires_at')

    # HubSpot - restore old column first
    with op.batch_alter_table('hubspot_credential', schema=None) as batch_op:
        batch_op.add_column(sa.Column('hubspot_refresh_token', sa.VARCHAR(length=255), nullable=True))
    
    # Copy data back
    hubspot_table = table('hubspot_credential',
        column('oauth_refresh_token', sa.String),
        column('hubspot_refresh_token', sa.String)
    )
    op.execute(
        hubspot_table.update().values(hubspot_refresh_token=hubspot_table.c.oauth_refresh_token)
    )
    
    # Make it NOT NULL and drop new columns
    with op.batch_alter_table('hubspot_credential', schema=None) as batch_op:
        batch_op.alter_column('hubspot_refresh_token', nullable=False)
        batch_op.drop_column('oauth_token_expires_at')
        batch_op.drop_column('oauth_access_token')
        batch_op.drop_column('oauth_refresh_token')

    # Google - restore old column first
    with op.batch_alter_table('google_credential', schema=None) as batch_op:
        batch_op.add_column(sa.Column('refresh_token', sa.VARCHAR(length=255), nullable=True))
    
    # Copy data back
    google_table = table('google_credential',
        column('oauth_refresh_token', sa.String),
        column('refresh_token', sa.String)
    )
    op.execute(
        google_table.update().values(refresh_token=google_table.c.oauth_refresh_token)
    )
    
    # Make it NOT NULL and drop new columns
    with op.batch_alter_table('google_credential', schema=None) as batch_op:
        batch_op.alter_column('refresh_token', nullable=False)
        batch_op.drop_column('oauth_token_expires_at')
        batch_op.drop_column('oauth_access_token')
        batch_op.drop_column('oauth_refresh_token')

    op.drop_table('rapidapi_credential')
    # ### end Alembic commands ###