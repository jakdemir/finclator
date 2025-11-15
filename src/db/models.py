"""SQLAlchemy ORM models for Finclator entities."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Boolean,
    Numeric,
    ForeignKey,
    Enum,
    ARRAY,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .session import Base


# Enums
class Direction(PyEnum):
    """Sentiment direction."""
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"


class Horizon(PyEnum):
    """Time horizon for predictions."""
    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    LONG = "LONG"
    OVERALL = "OVERALL"


class Outcome(PyEnum):
    """Prediction evaluation outcome."""
    CORRECT = "CORRECT"
    WRONG = "WRONG"
    UNCLEAR = "UNCLEAR"


# Models
class FinanceSchool(Base):
    """Finance theory school or worldview."""
    __tablename__ = "finance_schools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    influencers: Mapped[list["Influencer"]] = relationship("Influencer", back_populates="finance_school")


class Influencer(Base):
    """Person or account whose market commentary is analyzed."""
    __tablename__ = "influencers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    handle: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    finance_school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("finance_schools.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    finance_school: Mapped["FinanceSchool"] = relationship("FinanceSchool", back_populates="influencers")
    tweets: Mapped[list["Tweet"]] = relationship("Tweet", back_populates="influencer")
    trust_scores: Mapped[list["TrustScore"]] = relationship("TrustScore", back_populates="influencer")


class Tweet(Base):
    """Tweet from an influencer."""
    __tablename__ = "tweets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    influencer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("influencers.id"), nullable=False
    )
    tweet_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tweeted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    asset_symbols: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    processed_for_sentiment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    influencer: Mapped["Influencer"] = relationship("Influencer", back_populates="tweets")
    sentiment_predictions: Mapped[list["SentimentPrediction"]] = relationship(
        "SentimentPrediction", back_populates="tweet"
    )


class SentimentPrediction(Base):
    """Extracted sentiment prediction from a tweet."""
    __tablename__ = "sentiment_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tweet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tweets.id"), nullable=False
    )
    asset_symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    direction: Mapped[Direction] = mapped_column(Enum(Direction), nullable=False)
    horizon: Mapped[Horizon] = mapped_column(Enum(Horizon), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    matures_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    evaluated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    tweet: Mapped["Tweet"] = relationship("Tweet", back_populates="sentiment_predictions")
    prediction_outcome: Mapped[Optional["PredictionOutcome"]] = relationship(
        "PredictionOutcome", back_populates="sentiment_prediction", uselist=False
    )


class PriceCandle(Base):
    """OHLCV price data for an asset."""
    __tablename__ = "price_candles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    open: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[Optional[float]] = mapped_column(Numeric(20, 8), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)


class PredictionOutcome(Base):
    """Evaluation of a sentiment prediction against actual price movements."""
    __tablename__ = "prediction_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sentiment_prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sentiment_predictions.id"), unique=True, nullable=False
    )
    asset_symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    horizon: Mapped[Horizon] = mapped_column(Enum(Horizon), nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    exit_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    return_pct: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    outcome: Mapped[Outcome] = mapped_column(Enum(Outcome), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    evaluation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    sentiment_prediction: Mapped["SentimentPrediction"] = relationship(
        "SentimentPrediction", back_populates="prediction_outcome"
    )


class TrustScore(Base):
    """Performance-based trust score for an influencer."""
    __tablename__ = "trust_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    influencer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("influencers.id"), nullable=False
    )
    asset_symbol: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    horizon: Mapped[Horizon] = mapped_column(Enum(Horizon), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    influencer: Mapped["Influencer"] = relationship("Influencer", back_populates="trust_scores")


class CurrentSignal(Base):
    """Current aggregated signal for an asset and horizon."""
    __tablename__ = "current_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    horizon: Mapped[Horizon] = mapped_column(Enum(Horizon), nullable=False)
    finance_school_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("finance_schools.id"), nullable=True
    )
    weighted_score_buy: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    weighted_score_neutral: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    weighted_score_sell: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    final_label: Mapped[Direction] = mapped_column(Enum(Direction), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    finance_school: Mapped[Optional["FinanceSchool"]] = relationship("FinanceSchool")

