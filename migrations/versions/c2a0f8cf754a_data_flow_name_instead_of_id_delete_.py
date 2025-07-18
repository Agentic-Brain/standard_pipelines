"""data flow name instead of id; delete webhook_id

Revision ID: c2a0f8cf754a
Revises: a9c4adc80188
Create Date: 2025-01-31 19:47:27.916698

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2a0f8cf754a'
down_revision = 'a9c4adc80188'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('client_data_flow_join', schema=None) as batch_op:
        batch_op.drop_column('webhook_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('client_data_flow_join', schema=None) as batch_op:
        batch_op.add_column(sa.Column('webhook_id', sa.VARCHAR(length=255), autoincrement=False, nullable=False))

    # ### end Alembic commands ###
