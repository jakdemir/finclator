"""API routes for market signals."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.session import get_db
from src.db.models import CurrentSignal, Horizon, Direction
from src.db.schema import SignalResponse, SchoolSignal
from src.services.logging import logger

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=SignalResponse, include_in_schema=True)
async def get_signal(
    asset: str = Query(..., description="Asset symbol (BTC, GOLD, SPX)"),
    horizon: str = Query(..., description="Time horizon (SHORT, MEDIUM, LONG)"),
    session: AsyncSession = Depends(get_db),
):
    """
    Get current aggregated signal for an asset and horizon.
    
    Returns the overall (across all finance schools) Buy/Neutral/Sell indicator.
    """
    # Validate asset
    if asset not in ["BTC", "GOLD", "SPX"]:
        raise HTTPException(status_code=400, detail=f"Invalid asset: {asset}. Must be BTC, GOLD, or SPX")
    
    # Validate horizon
    try:
        horizon_enum = Horizon[horizon.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400, detail=f"Invalid horizon: {horizon}. Must be SHORT, MEDIUM, or LONG"
        )
    
    # Get overall signal (finance_school_id is None)
    # Order by generated_at DESC and limit to 1 to get the most recent if multiple exist
    result = await session.execute(
        select(CurrentSignal).where(
            CurrentSignal.asset_symbol == asset,
            CurrentSignal.horizon == horizon_enum,
            CurrentSignal.finance_school_id.is_(None),
        ).order_by(CurrentSignal.generated_at.desc()).limit(1)
    )
    signal = result.scalar_one_or_none()
    
    if not signal:
        # Return N/A response per NFR-003
        raise HTTPException(
            status_code=404,
            detail=f"No signal available for {asset} {horizon}. Data may be insufficient.",
        )
    
    return SignalResponse(
        asset=signal.asset_symbol,
        horizon=signal.horizon.value,
        final_label=signal.final_label.value,
        weighted_score_buy=float(signal.weighted_score_buy),
        weighted_score_neutral=float(signal.weighted_score_neutral),
        weighted_score_sell=float(signal.weighted_score_sell),
        generated_at=signal.generated_at,
    )


@router.get("/school-signals", response_model=list[SchoolSignal])
async def get_school_signals(
    asset: str = Query(..., description="Asset symbol (BTC, GOLD, SPX)"),
    horizon: str = Query(..., description="Time horizon (SHORT, MEDIUM, LONG)"),
    session: AsyncSession = Depends(get_db),
):
    """
    Get school-level signals for an asset and horizon.
    
    Returns signals broken down by finance school.
    """
    # Validate asset
    if asset not in ["BTC", "GOLD", "SPX"]:
        raise HTTPException(status_code=400, detail=f"Invalid asset: {asset}. Must be BTC, GOLD, or SPX")
    
    # Validate horizon
    try:
        horizon_enum = Horizon[horizon.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400, detail=f"Invalid horizon: {horizon}. Must be SHORT, MEDIUM, or LONG"
        )
    
    # Get all school-level signals (finance_school_id is not None)
    # Use outerjoin to handle cases where finance_school might be deleted
    from src.db.models import FinanceSchool
    result = await session.execute(
        select(CurrentSignal, FinanceSchool.name)
        .outerjoin(FinanceSchool, CurrentSignal.finance_school_id == FinanceSchool.id)
        .where(
            CurrentSignal.asset_symbol == asset,
            CurrentSignal.horizon == horizon_enum,
            CurrentSignal.finance_school_id.isnot(None),
        )
    )
    signal_rows = result.all()
    
    if not signal_rows:
        # Return empty list if no data
        return []
    
    # Convert to response models
    school_signals = []
    for signal, school_name in signal_rows:
        school_signals.append(
            SchoolSignal(
                finance_school=school_name or "Unknown",
                asset=signal.asset_symbol,
                horizon=signal.horizon.value,
                final_label=signal.final_label.value,
                weighted_score_buy=float(signal.weighted_score_buy),
                weighted_score_neutral=float(signal.weighted_score_neutral),
                weighted_score_sell=float(signal.weighted_score_sell),
                generated_at=signal.generated_at,
            )
        )
    
    return school_signals

