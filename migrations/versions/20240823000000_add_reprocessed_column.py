"""Add reprocessed column

Revision ID: 20240823000000
Revises: 20240822165438_add_hr_and_calories_columns
Create Date: 2025-08-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240823000000'
down_revision = '20240822165438_add_hr_and_calories_columns'
branch_labels = None
depends_on = None

def upgrade():
    # Add reprocessed column to activities table
    op.add_column('activities', sa.Column('reprocessed', sa.Boolean(), nullable=True, server_default='0'))
    
    # Set default value for existing records
    op.execute("UPDATE activities SET reprocessed = 0 WHERE reprocessed IS NULL")
    
    # Make the column NOT NULL after setting default values
    with op.batch_alter_table('activities') as batch_op:
        batch_op.alter_column('reprocessed', existing_type=sa.Boolean(), nullable=False)

def downgrade():
    # Remove reprocessed column
    with op.batch_alter_table('activities') as batch_op:
        batch_op.drop_column('reprocessed')
