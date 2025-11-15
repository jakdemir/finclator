"""Structured logging configuration for Finclator."""
import logging
import sys
from typing import Optional

from .config import settings


def setup_logging(log_level: Optional[str] = None):
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level = log_level or settings.log_level
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return root_logger


# Module-level logger
logger = logging.getLogger("finclator")


def log_classification(
    tweet_id: str, asset: str, direction: str, horizon: str, confidence: float
):
    """Log sentiment classification decision."""
    logger.info(
        f"CLASSIFICATION: tweet_id={tweet_id} asset={asset} "
        f"direction={direction} horizon={horizon} confidence={confidence:.2f}"
    )


def log_evaluation(
    prediction_id: str, asset: str, outcome: str, entry: float, exit: float, return_pct: float
):
    """Log prediction evaluation result."""
    logger.info(
        f"EVALUATION: prediction_id={prediction_id} asset={asset} "
        f"outcome={outcome} entry={entry:.2f} exit={exit:.2f} return={return_pct:.2f}%"
    )


def log_aggregation(asset: str, horizon: str, signal: str, buy: float, neutral: float, sell: float):
    """Log signal aggregation outcome."""
    logger.info(
        f"AGGREGATION: asset={asset} horizon={horizon} signal={signal} "
        f"buy={buy:.3f} neutral={neutral:.3f} sell={sell:.3f}"
    )


def log_trust_update(influencer_id: str, asset: Optional[str], horizon: str, old_score: float, new_score: float):
    """Log trust score update."""
    logger.info(
        f"TRUST_UPDATE: influencer_id={influencer_id} asset={asset or 'ALL'} "
        f"horizon={horizon} old_score={old_score:.3f} new_score={new_score:.3f}"
    )

