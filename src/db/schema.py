"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SignalResponse(BaseModel):
    """Response schema for /signals endpoint."""
    
    asset: str = Field(..., description="Asset symbol (BTC, GOLD, SPX)")
    horizon: str = Field(..., description="Time horizon (SHORT, MEDIUM, LONG)")
    final_label: str = Field(..., description="Final signal (BUY, NEUTRAL, SELL)")
    weighted_score_buy: float = Field(..., description="Weighted buy score")
    weighted_score_neutral: float = Field(..., description="Weighted neutral score")
    weighted_score_sell: float = Field(..., description="Weighted sell score")
    generated_at: datetime = Field(..., description="Timestamp when signal was generated")

    class Config:
        from_attributes = True


class SchoolSignal(BaseModel):
    """School-level signal breakdown."""
    
    finance_school: str = Field(..., description="Finance school name")
    asset: str = Field(..., description="Asset symbol (BTC, GOLD, SPX)")
    horizon: str = Field(..., description="Time horizon (SHORT, MEDIUM, LONG)")
    final_label: str = Field(..., description="Final signal (BUY, NEUTRAL, SELL)")
    weighted_score_buy: float = Field(..., description="Weighted buy score")
    weighted_score_neutral: float = Field(..., description="Weighted neutral score")
    weighted_score_sell: float = Field(..., description="Weighted sell score")
    generated_at: datetime = Field(..., description="Timestamp when signal was generated")

    class Config:
        from_attributes = True


class TrustScoreDetail(BaseModel):
    """Trust score details for an influencer."""
    
    asset_symbol: Optional[str] = Field(None, description="Asset symbol or null for overall")
    horizon: str = Field(..., description="Time horizon (SHORT, MEDIUM, LONG, OVERALL)")
    score: float = Field(..., description="Trust score value")

    class Config:
        from_attributes = True


class RecentPrediction(BaseModel):
    """Recent prediction with outcome for an influencer."""
    
    asset_symbol: str = Field(..., description="Asset symbol")
    horizon: str = Field(..., description="Time horizon")
    direction: str = Field(..., description="Prediction direction (BUY, NEUTRAL, SELL)")
    tweeted_at: datetime = Field(..., description="Tweet timestamp")
    outcome: Optional[str] = Field(None, description="Outcome (CORRECT, WRONG, UNCLEAR)")

    class Config:
        from_attributes = True


class InfluencerResponse(BaseModel):
    """Response schema for /influencers/{id} endpoint."""
    
    id: UUID = Field(..., description="Influencer ID")
    handle: str = Field(..., description="X handle")
    display_name: str = Field(..., description="Display name")
    finance_school: str = Field(..., description="Finance school name")
    current_trust_scores: list[TrustScoreDetail] = Field(
        default_factory=list, description="Current trust scores"
    )
    recent_predictions: list[RecentPrediction] = Field(
        default_factory=list, description="Recent predictions"
    )

    class Config:
        from_attributes = True

