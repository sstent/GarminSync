"""Add avg_heart_rate and calories columns to activities table

Revision ID: 20240822165438
Revises: 20240821150000
Create Date: 2024-08-22 16:54:38.123456

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240822165438'
down_revision = '20240821150000'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('activities', sa.Column('avg_heart_rate', sa.Integer(), nullable=True))
    op.add_column('activities', sa.Column('calories', sa.Integer(), nullable=True))

def downgrade():
    op.drop_column('activities', 'avg_heart_rate')
    op.drop_column('activities', 'calories')
