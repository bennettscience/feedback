"""remove complete bool from standard

Revision ID: c309107ec8d2
Revises: d4ff12af3701
Create Date: 2023-06-29 15:36:13.626148

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c309107ec8d2'
down_revision = 'd4ff12af3701'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('standard', schema=None) as batch_op:
        batch_op.drop_column('is_complete')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('standard', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_complete', sa.BOOLEAN(), nullable=True))

    # ### end Alembic commands ###
