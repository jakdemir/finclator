"""API routes for dashboard data."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from src.db.session import get_db
from src.db.models import CurrentSignal, Influencer, TrustScore, Horizon
from src.services.logging import logger

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/signals")
async def get_dashboard_signals(
    session: AsyncSession = Depends(get_db),
):
    """Get all current signals for dashboard."""
    result = await session.execute(
        select(CurrentSignal)
        .where(CurrentSignal.finance_school_id.is_(None))  # Overall signals only
        .order_by(CurrentSignal.asset_symbol, CurrentSignal.horizon)
    )
    signals = result.scalars().all()
    
    return [
        {
            "asset": s.asset_symbol,
            "horizon": s.horizon.value,
            "final_label": s.final_label.value,
            "weighted_score_buy": float(s.weighted_score_buy),
            "weighted_score_neutral": float(s.weighted_score_neutral),
            "weighted_score_sell": float(s.weighted_score_sell),
        }
        for s in signals
    ]


@router.get("/influencers")
async def get_dashboard_influencers(
    session: AsyncSession = Depends(get_db),
):
    """Get influencers with average trust scores for dashboard - only those with tweets."""
    result = await session.execute(
        text('''
            SELECT 
                i.handle,
                i.display_name,
                AVG(ts.score) as avg_trust,
                COUNT(DISTINCT t.id) as tweet_count
            FROM influencers i
            INNER JOIN tweets t ON i.id = t.influencer_id
            LEFT JOIN trust_scores ts ON i.id = ts.influencer_id
            GROUP BY i.id, i.handle, i.display_name
            HAVING COUNT(DISTINCT t.id) > 0
            ORDER BY avg_trust DESC NULLS LAST
        ''')
    )
    
    influencers = []
    for row in result:
        influencers.append({
            "handle": row.handle,
            "display_name": row.display_name,
            "avg_trust": float(row.avg_trust) if row.avg_trust else 0.5,
            "tweet_count": row.tweet_count,
        })
    
    return influencers

