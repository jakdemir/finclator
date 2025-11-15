"""Price data provider integration with Alpha Vantage."""
from datetime import datetime
from typing import List, Dict, Any, Optional

from .config import settings
from .http_client import http_client
from .api_cache import api_cache


class PriceProvider:
    """Alpha Vantage integration for OHLCV price data."""
    
    ASSET_SYMBOLS_MAP = {
        "BTC": "BTC",  # Crypto symbol
        "GOLD": "GLD",  # Gold ETF as proxy
        "SPX": "SPY",  # S&P 500 ETF as proxy
    }
    
    def __init__(self):
        """Initialize price provider with Alpha Vantage API key."""
        self.api_key = settings.alphavantage_api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    async def fetch_daily_candles(
        self, asset_symbol: str, outputsize: str = "compact"
    ) -> List[Dict[str, Any]]:
        """
        Fetch daily OHLCV candles for an asset.
        
        Args:
            asset_symbol: Asset symbol (BTC, GOLD, SPX)
            outputsize: 'compact' (last 100 days) or 'full' (20+ years)
            
        Returns:
            List of candle dicts with timestamp, open, high, low, close, volume
        """
        if asset_symbol not in self.ASSET_SYMBOLS_MAP:
            raise ValueError(f"Unknown asset symbol: {asset_symbol}")
        
        # Map to Alpha Vantage symbol
        av_symbol = self.ASSET_SYMBOLS_MAP[asset_symbol]
        
        # Choose function based on asset type
        if asset_symbol == "BTC":
            function = "DIGITAL_CURRENCY_DAILY"
            params = {
                "function": function,
                "symbol": av_symbol,
                "market": "USD",
                "apikey": self.api_key,
            }
        else:
            function = "TIME_SERIES_DAILY"
            params = {
                "function": function,
                "symbol": av_symbol,
                "outputsize": outputsize,
                "apikey": self.api_key,
            }
        
        try:
            # Check cache first
            cache_key = {
                'asset': asset_symbol,
                'outputsize': outputsize
            }
            cached_data = await api_cache.get('alphavantage', cache_key)
            
            if cached_data:
                data = cached_data
            else:
                response = await http_client.get(self.base_url, params=params)
                data = response.json()
                # Cache the response
                await api_cache.set('alphavantage', cache_key, data)
            
            # Parse response based on function type
            if function == "DIGITAL_CURRENCY_DAILY":
                time_series_key = "Time Series (Digital Currency Daily)"
            else:
                time_series_key = "Time Series (Daily)"
            
            if time_series_key not in data:
                print(f"Alpha Vantage error: {data.get('Note', data.get('Error Message', 'Unknown error'))}")
                return []
            
            time_series = data[time_series_key]
            candles = []
            
            for date_str, values in time_series.items():
                # Parse response - Alpha Vantage uses same keys for both crypto and stocks
                # Keys are: "1. open", "2. high", "3. low", "4. close", "5. volume"
                candle = {
                    "timestamp": datetime.fromisoformat(date_str),
                    "open": float(values.get("1. open", 0)),
                    "high": float(values.get("2. high", 0)),
                    "low": float(values.get("3. low", 0)),
                    "close": float(values.get("4. close", 0)),
                    "volume": float(values.get("5. volume", 0)),
                    "asset_symbol": asset_symbol,
                    "source": "AlphaVantage",
                }
                
                candles.append(candle)
            
            return candles
        except Exception as e:
            print(f"Price fetch error for {asset_symbol}: {e}")
            return []


# Global price provider instance
price_provider = PriceProvider()

