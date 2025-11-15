"""API endpoints for influencers."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Influencer, FinanceSchool, Tweet
from src.db.schema import InfluencerResponse, TrustScoreDetail, RecentPrediction
from src.api.dependencies import get_db_session
from src.services.trust_scoring import get_all_trust_scores, get_recent_predictions_with_outcomes


router = APIRouter(prefix="/influencers", tags=["influencers"])


@router.get("/{influencer_id}", response_model=InfluencerResponse)
async def get_influencer(
    influencer_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get detailed information about an influencer.
    
    Returns influencer details, current trust scores, and recent predictions.
    """
    # Fetch influencer with finance school
    result = await session.execute(
        select(Influencer, FinanceSchool.name)
        .join(FinanceSchool, Influencer.finance_school_id == FinanceSchool.id)
        .where(Influencer.id == influencer_id)
    )
    
    influencer_and_school = result.first()
    
    if not influencer_and_school:
        raise HTTPException(
            status_code=404,
            detail=f"Influencer {influencer_id} not found"
        )
    
    influencer, school_name = influencer_and_school
    
    # Fetch all trust scores
    trust_scores = await get_all_trust_scores(session, influencer_id)
    
    trust_score_details = [
        TrustScoreDetail(
            asset_symbol=ts.asset_symbol,
            horizon=ts.horizon.value,
            score=float(ts.score),
        )
        for ts in trust_scores
    ]
    
    # Fetch recent predictions with outcomes
    predictions_with_outcomes = await get_recent_predictions_with_outcomes(
        session, influencer_id, limit=10
    )
    
    # Fetch tweet created_at timestamps for predictions
    recent_predictions = []
    for prediction, outcome in predictions_with_outcomes:
        # Get tweet for timestamp
        tweet_result = await session.execute(
            select(Tweet.tweeted_at)
            .where(Tweet.id == prediction.tweet_id)
        )
        tweet = tweet_result.scalar_one_or_none()
        
        recent_predictions.append(
            RecentPrediction(
                asset_symbol=prediction.asset_symbol,
                horizon=prediction.horizon.value,
                direction=prediction.direction.value,
                tweeted_at=tweet if tweet else prediction.created_at,
                outcome=outcome.outcome.value if outcome else None,
            )
        )
    
    return InfluencerResponse(
        id=influencer.id,
        handle=influencer.handle,
        display_name=influencer.display_name,
        finance_school=school_name,
        current_trust_scores=trust_score_details,
        recent_predictions=recent_predictions,
    )


@router.get("", response_model=list[dict])
async def list_influencers(
    session: AsyncSession = Depends(get_db_session),
):
    """
    List all influencers with basic information.
    
    Returns a list of influencers with their ID, handle, display name, and finance school.
    """
    result = await session.execute(
        select(Influencer, FinanceSchool.name)
        .join(FinanceSchool, Influencer.finance_school_id == FinanceSchool.id)
        .order_by(Influencer.display_name)
    )
    
    influencers_and_schools = result.all()
    
    return [
        {
            "id": str(influencer.id),
            "handle": influencer.handle,
            "display_name": influencer.display_name,
            "finance_school": school_name,
        }
        for influencer, school_name in influencers_and_schools
    ]

