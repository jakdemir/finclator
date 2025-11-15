"""Add unique constraints for upserts

Revision ID: abd67b70e7b2
Revises: a1298e7618c1
Create Date: 2025-11-15 14:30:49.068858

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abd67b70e7b2'
down_revision = 'a1298e7618c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unique constraint for price_candles upserts
    op.create_unique_constraint(
        'uq_price_candles_asset_timestamp',
        'price_candles',
        ['asset_symbol', 'timestamp']
    )
    
    # Add unique constraint for current_signals upserts
    # Note: This handles NULL finance_school_id (overall signals) correctly
    op.create_unique_constraint(
        'uq_current_signals_asset_horizon_school',
        'current_signals',
        ['asset_symbol', 'horizon', 'finance_school_id']
    )


def downgrade() -> None:
    # Remove unique constraints
    op.drop_constraint('uq_current_signals_asset_horizon_school', 'current_signals', type_='unique')
    op.drop_constraint('uq_price_candles_asset_timestamp', 'price_candles', type_='unique')

