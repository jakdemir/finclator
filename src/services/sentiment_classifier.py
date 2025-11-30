"""Sentiment classification service using Hugging Face models or agent-based (OpenAI)."""
import json
import re
from typing import Dict, Any, Optional

from huggingface_hub import InferenceClient

from src.services.config import settings
from src.services.logging import logger
from src.services.api_cache import api_cache

# Try to import OpenAI for agent-based sentiment
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class SentimentClassifier:
    """Wrapper for sentiment classification using Hugging Face models or agent-based (OpenAI)."""
    
    def __init__(self):
        """Initialize sentiment classifier."""
        self.use_agent = settings.use_agent_sentiment and OPENAI_AVAILABLE and settings.openai_api_key
        
        if self.use_agent:
            self.agent_client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info("Using agent-based sentiment classification (OpenAI)")
        else:
            self.client = InferenceClient(token=settings.huggingface_api_key)
            # Financial sentiment model - configurable via SENTIMENT_MODEL env var
            self.sentiment_model = settings.sentiment_model
            logger.info(f"Using HuggingFace model: {self.sentiment_model}")
        
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
        Classify sentiment into BUY/NEUTRAL/SELL using agent-based or model-based approach.
        
        Args:
            tweet_text: Tweet text to classify
            asset_symbol: Asset being discussed (BTC, GOLD, SPX)
            
        Returns:
            Dict with direction (BUY/NEUTRAL/SELL), horizon (SHORT/MEDIUM/LONG),
            and confidence score, or None if classification fails
        """
        logger.info(f"Classifying sentiment for {asset_symbol}: {tweet_text[:50]}...")
        
        if self.use_agent:
            return await self._classify_with_agent(tweet_text, asset_symbol)
        else:
            return await self._classify_with_model(tweet_text, asset_symbol)
    
    async def _classify_with_agent(
        self,
        tweet_text: str,
        asset_symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Use agent-based (OpenAI) classification for more nuanced analysis."""
        try:
            # Check cache first
            cache_key = {
                'text': tweet_text,
                'asset': asset_symbol,
                'model': 'openai-agent'
            }
            cached_result = await api_cache.get('openai', cache_key)
            
            if cached_result:
                result = cached_result
            else:
                # Use OpenAI with structured output for agent-based analysis
                prompt = f"""Analyze this financial tweet about {asset_symbol} and determine:
1. Sentiment direction: BUY (bullish/positive), SELL (bearish/negative), or NEUTRAL
2. Time horizon: SHORT (0-3 months), MEDIUM (3-12 months), or LONG (1+ years)
3. Confidence: 0.0 to 1.0

Tweet: "{tweet_text}"

Respond in JSON format:
{{
    "direction": "BUY|NEUTRAL|SELL",
    "horizon": "SHORT|MEDIUM|LONG",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""

                response = await self.agent_client.chat.completions.create(
                    model="gpt-4o-mini",  # Fast and cost-effective
                    messages=[
                        {"role": "system", "content": "You are a financial sentiment analyst. Analyze tweets for market sentiment and time horizons. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                
                result_text = response.choices[0].message.content
                result = json.loads(result_text)
                
                # Cache the result
                await api_cache.set('openai', cache_key, result)
            
            direction = result.get('direction', 'NEUTRAL').upper()
            horizon = result.get('horizon', 'MEDIUM').upper()
            confidence = float(result.get('confidence', 0.5))
            
            # Validate direction and horizon
            if direction not in ['BUY', 'SELL', 'NEUTRAL']:
                direction = 'NEUTRAL'
            if horizon not in ['SHORT', 'MEDIUM', 'LONG']:
                horizon = self._detect_horizon(tweet_text)
            
            logger.info(f"Agent classified as {direction} ({horizon}) with confidence {confidence:.2f}")
            
            return {
                "direction": direction,
                "horizon": horizon,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error in agent classification: {e}")
            return None
    
    async def _classify_with_model(
        self,
        tweet_text: str,
        asset_symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Use HuggingFace model for classification."""
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
                # Use configured model for financial sentiment
                result = self.client.text_classification(
                    tweet_text,
                    model=self.sentiment_model
                )
                # Cache the result
                await api_cache.set('huggingface', cache_key, result)
            
            # Model returns: positive/negative/neutral (or similar) with scores
            # Map sentiment labels to actionable signals
            label = result[0]['label'].lower()
            confidence = result[0]['score']
            
            # Map model labels to our direction (handles various model outputs)
            # Twitter RoBERTa uses: LABEL_0 (negative), LABEL_1 (neutral), LABEL_2 (positive)
            # FinBERT uses: positive, negative, neutral
            direction_map = {
                'positive': 'BUY',
                'label_2': 'BUY',  # Twitter RoBERTa positive
                'bullish': 'BUY',
                'buy': 'BUY',
                'negative': 'SELL',
                'label_0': 'SELL',  # Twitter RoBERTa negative
                'bearish': 'SELL',
                'sell': 'SELL',
                'neutral': 'NEUTRAL',
                'label_1': 'NEUTRAL',  # Twitter RoBERTa neutral
                'lab_0': 'NEUTRAL',  # Alternative numeric labels
                'lab_1': 'BUY',
                'lab_2': 'SELL',
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
