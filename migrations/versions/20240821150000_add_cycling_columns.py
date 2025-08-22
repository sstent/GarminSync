from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('power_analysis', sa.Column('peak_power_1s', sa.Float(), nullable=True))
    op.add_column('power_analysis', sa.Column('peak_power_5s', sa.Float(), nullable=True))
    op.add_column('power_analysis', sa.Column('peak_power_20s', sa.Float(), nullable=True))
    op.add_column('power_analysis', sa.Column('peak_power_300s', sa.Float(), nullable=True))
    op.add_column('power_analysis', sa.Column('normalized_power', sa.Float(), nullable=True))
    op.add_column('power_analysis', sa.Column('intensity_factor', sa.Float(), nullable=True))
    op.add_column('power_analysis', sa.Column('training_stress_score', sa.Float(), nullable=True))

    op.add_column('gearing_analysis', sa.Column('estimated_chainring_teeth', sa.Integer(), nullable=True))
    op.add_column('gearing_analysis', sa.Column('estimated_cassette_teeth', sa.Integer(), nullable=True))
    op.add_column('gearing_analysis', sa.Column('gear_ratio', sa.Float(), nullable=True))
    op.add_column('gearing_analysis', sa.Column('gear_inches', sa.Float(), nullable=True))
    op.add_column('gearing_analysis', sa.Column('development_meters', sa.Float(), nullable=True))
    op.add_column('gearing_analysis', sa.Column('confidence_score', sa.Float(), nullable=True))
    op.add_column('gearing_analysis', sa.Column('analysis_method', sa.String(), default="singlespeed_estimation"))

def downgrade():
    op.drop_column('power_analysis', 'peak_power_1s')
    op.drop_column('power_analysis', 'peak_power_5s')
    op.drop_column('power_analysis', 'peak_power_20s')
    op.drop_column('power_analysis', 'peak_power_300s')
    op.drop_column('power_analysis', 'normalized_power')
    op.drop_column('power_analysis', 'intensity_factor')
    op.drop_column('power_analysis', 'training_stress_score')

    op.drop_column('gearing_analysis', 'estimated_chainring_teeth')
    op.drop_column('gearing_analysis', 'estimated_cassette_teeth')
    op.drop_column('gearing_analysis', 'gear_ratio')
    op.drop_column('gearing_analysis', 'gear_inches')
    op.drop_column('gearing_analysis', 'development_meters')
    op.drop_column('gearing_analysis', 'confidence_score')
    op.drop_column('gearing_analysis', 'analysis_method')
