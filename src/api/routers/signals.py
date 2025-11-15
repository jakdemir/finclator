"""API endpoints for signals."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.db.models import CurrentSignal, Horizon, FinanceSchool
from src.db.schema import SignalResponse, SchoolSignal
from src.api.dependencies import get_db_session


router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=SignalResponse)
async def get_signal(
    asset: str = Query(..., description="Asset symbol (BTC, GOLD, SPX)"),
    horizon: str = Query(..., description="Time horizon (SHORT, MEDIUM, LONG)"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get current aggregated signal for an asset and horizon.
    
    Returns the overall signal (combined across all finance schools).
    """
    # Validate inputs
    if asset not in ["BTC", "GOLD", "SPX"]:
        raise HTTPException(status_code=400, detail=f"Invalid asset: {asset}")
    
    try:
        horizon_enum = Horizon[horizon.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid horizon: {horizon}")
    
    # Query for overall signal (finance_school_id is null)
    result = await session.execute(
        select(CurrentSignal)
        .where(CurrentSignal.asset_symbol == asset)
        .where(CurrentSignal.horizon == horizon_enum)
        .where(CurrentSignal.finance_school_id.is_(None))
        .order_by(CurrentSignal.generated_at.desc())
        .limit(1)
    )
    
    signal = result.scalar_one_or_none()
    
    if not signal:
        raise HTTPException(
            status_code=404,
            detail=f"No signal found for {asset}/{horizon}. Run aggregation worker first."
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
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get school-level signal breakdown for an asset and horizon.
    
    Returns signals broken down by finance school (Macro, Technical, Value, Growth).
    """
    # Validate inputs
    if asset not in ["BTC", "GOLD", "SPX"]:
        raise HTTPException(status_code=400, detail=f"Invalid asset: {asset}")
    
    try:
        horizon_enum = Horizon[horizon.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid horizon: {horizon}")
    
    # Query for school-specific signals (finance_school_id is not null)
    result = await session.execute(
        select(CurrentSignal, FinanceSchool.name)
        .join(FinanceSchool, CurrentSignal.finance_school_id == FinanceSchool.id)
        .where(CurrentSignal.asset_symbol == asset)
        .where(CurrentSignal.horizon == horizon_enum)
        .where(CurrentSignal.finance_school_id.is_not(None))
        .order_by(FinanceSchool.name)
    )
    
    signals_and_schools = result.all()
    
    if not signals_and_schools:
        raise HTTPException(
            status_code=404,
            detail=f"No school signals found for {asset}/{horizon}. Run aggregation worker first."
        )
    
    return [
        SchoolSignal(
            finance_school=school_name,
            asset=signal.asset_symbol,
            horizon=signal.horizon.value,
            final_label=signal.final_label.value,
            weighted_score_buy=float(signal.weighted_score_buy),
            weighted_score_neutral=float(signal.weighted_score_neutral),
            weighted_score_sell=float(signal.weighted_score_sell),
            generated_at=signal.generated_at,
        )
        for signal, school_name in signals_and_schools
    ]

