"""Sentiment classification service using Hugging Face models."""
import json
import re
from typing import Dict, Any, Optional

from huggingface_hub import InferenceClient

from src.services.config import settings
from src.services.logging import logger
from src.services.api_cache import api_cache


class SentimentClassifier:
    """Wrapper for sentiment classification using Hugging Face models."""
    
    def __init__(self):
        """Initialize sentiment classifier with Hugging Face client."""
        self.client = InferenceClient(token=settings.huggingface_api_key)
        # Financial sentiment model (bullish/bearish/neutral)
        self.sentiment_model = "ProsusAI/finbert"
        
    async def is_market_relevant(self, tweet_text: str) -> bool:
        """
        Filter out noise (non-market-related tweets).
        
        Uses keyword matching to quickly filter irrelevant content.
        
        Args:
            tweet_text: Raw tweet text
            
        Returns:
            True if tweet is relevant for sentiment analysis, False otherwise
        """
        # Quick keyword-based filtering for efficiency
        text_lower = tweet_text.lower()
        
        # Market-related keywords
        market_keywords = [
            'btc', 'bitcoin', 'crypto', 'gold', 'spy', 's&p', 'stock', 'market',
            'buy', 'sell', 'bullish', 'bearish', 'price', 'rally', 'dump', 'pump',
            'breakout', 'support', 'resistance', 'ath', 'crash', 'moon', 'dip',
            'trading', 'invest', 'portfolio', 'bull', 'bear', 'long', 'short',
            'fed', 'inflation', 'rates', 'economy', 'recession'
        ]
        
        # Check if any market keyword is present
        has_market_keyword = any(keyword in text_lower for keyword in market_keywords)
        
        if has_market_keyword:
            logger.info(f"✓ Tweet passed filter: {tweet_text[:50]}...")
            return True
        else:
            logger.info(f"✗ Tweet filtered out (no market keywords): {tweet_text[:50]}...")
            return False
    
    async def classify_sentiment(
        self, 
        tweet_text: str,
        asset_symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Classify sentiment into BUY/NEUTRAL/SELL using FinBERT.
        
        Args:
            tweet_text: Tweet text to classify
            asset_symbol: Asset being discussed (BTC, GOLD, SPX)
            
        Returns:
            Dict with direction (BUY/NEUTRAL/SELL), horizon (SHORT/MEDIUM/LONG),
            and confidence score, or None if classification fails
        """
        logger.info(f"Classifying sentiment for {asset_symbol}: {tweet_text[:50]}...")
        
        try:
            # Check cache first
            cache_key = {
                'text': tweet_text,
                'model': self.sentiment_model
            }
            cached_result = await api_cache.get('huggingface', cache_key)
            
            if cached_result:
                result = cached_result
            else:
                # Use FinBERT for financial sentiment
                result = self.client.text_classification(
                    tweet_text,
                    model=self.sentiment_model
                )
                # Cache the result
                await api_cache.set('huggingface', cache_key, result)
            
            # FinBERT returns: positive/negative/neutral with scores
            # Map financial sentiment to actionable signals
            label = result[0]['label'].lower()
            confidence = result[0]['score']
            
            # Map FinBERT labels to our direction
            direction_map = {
                'positive': 'BUY',
                'bullish': 'BUY',
                'negative': 'SELL',
                'bearish': 'SELL',
                'neutral': 'NEUTRAL'
            }
            direction = direction_map.get(label, 'NEUTRAL')
            
            # Detect time horizon from text
            horizon = self._detect_horizon(tweet_text)
            
            logger.info(f"Classified as {direction} ({horizon}) with confidence {confidence:.2f}")
            
            return {
                "direction": direction,
                "horizon": horizon,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error classifying sentiment: {e}")
            return None
    
    def _detect_horizon(self, text: str) -> str:
        """
        Detect time horizon from tweet text.
        
        Args:
            text: Tweet text
            
        Returns:
            SHORT, MEDIUM, or LONG
        """
        text_lower = text.lower()
        
        # Short-term indicators (0-3 months)
        short_keywords = [
            'today', 'tonight', 'tomorrow', 'this week', 'next week',
            'short term', 'day trade', 'swing', 'quick', 'now', 'immediate',
            'soon', 'coming days'
        ]
        
        # Long-term indicators (1-5+ years)
        long_keywords = [
            'long term', 'years', 'decade', 'cycle', 'secular', 'hold',
            'hodl', 'forever', 'generational', 'structural', 'secular',
            'next cycle', 'bull cycle', 'bear cycle'
        ]
        
        # Check for explicit horizon mentions
        if any(keyword in text_lower for keyword in short_keywords):
            return 'SHORT'
        elif any(keyword in text_lower for keyword in long_keywords):
            return 'LONG'
        
        # Check for specific time mentions using regex
        # Matches: "in X days/weeks/months/years"
        time_pattern = r'(\d+)\s*(day|week|month|year)s?'
        matches = re.findall(time_pattern, text_lower)
        
        if matches:
            number, unit = matches[0]
            number = int(number)
            
            if unit == 'day' or (unit == 'week' and number <= 8):
                return 'SHORT'
            elif unit == 'year' or (unit == 'month' and number > 12):
                return 'LONG'
            else:
                return 'MEDIUM'
        
        # Default to MEDIUM if no clear horizon detected
        return 'MEDIUM'


# Global sentiment classifier instance
sentiment_classifier = SentimentClassifier()
