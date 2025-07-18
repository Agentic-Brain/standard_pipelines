"""o365 creds

Revision ID: dc750294cad7
Revises: 4a90b922c1c5
Create Date: 2025-05-29 11:48:35.703731

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dc750294cad7'
down_revision = '4a90b922c1c5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('office365_credential',
    sa.Column('user_email', sa.String(length=255), nullable=False),
    sa.Column('user_name', sa.String(length=255), nullable=True),
    sa.Column('tenant_id', sa.String(length=255), nullable=True),
    sa.Column('user_principal_name', sa.String(length=255), nullable=True),
    sa.Column('oauth_refresh_token', sa.String(length=512), nullable=False),
    sa.Column('oauth_access_token', sa.String(length=512), nullable=True),
    sa.Column('oauth_token_expires_at', sa.Integer(), nullable=True),
    sa.Column('client_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['client.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('zoho_credential', schema=None) as batch_op:
        batch_op.drop_column('oauth_refresh_token')
        batch_op.drop_column('oauth_access_token')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('zoho_credential', schema=None) as batch_op:
        batch_op.add_column(sa.Column('oauth_access_token', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
        batch_op.add_column(sa.Column('oauth_refresh_token', sa.VARCHAR(length=255), autoincrement=False, nullable=False))

    op.drop_table('office365_credential')
    # ### end Alembic commands ###
