"""API response caching service to avoid rate limits."""
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, Dict
import asyncio

from src.services.logging import logger


class APICache:
    """
    Local filesystem cache for external API responses.
    
    Prevents hitting rate limits by caching responses locally.
    """
    
    def __init__(self, cache_dir: str = ".cache/api"):
        """
        Initialize API cache.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache TTLs (time-to-live) per API
        self.ttl_config = {
            "x_api": timedelta(days=90),           # Tweets: 3 months
            "alphavantage": timedelta(days=90),    # Prices: 3 months
            "huggingface": timedelta(days=90),     # Sentiment: 3 months (stable)
        }
    
    def _get_cache_key(self, api_name: str, request_params: Dict[str, Any]) -> str:
        """
        Generate cache key from API name and request parameters.
        
        Args:
            api_name: Name of the API (x_api, alphavantage, huggingface)
            request_params: Request parameters dict
            
        Returns:
            Hash-based cache key
        """
        # Sort params for consistent hashing
        param_str = json.dumps(request_params, sort_keys=True)
        hash_obj = hashlib.md5(f"{api_name}:{param_str}".encode())
        return hash_obj.hexdigest()
    
    def _get_cache_path(self, cache_key: str, api_name: str) -> Path:
        """Get file path for cache entry."""
        # Organize by API name in subdirectories
        api_dir = self.cache_dir / api_name
        api_dir.mkdir(exist_ok=True)
        return api_dir / f"{cache_key}.json"
    
    async def get(
        self, 
        api_name: str, 
        request_params: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Get cached response if valid.
        
        Args:
            api_name: Name of the API
            request_params: Request parameters
            
        Returns:
            Cached response data or None if not found/expired
        """
        cache_key = self._get_cache_key(api_name, request_params)
        cache_path = self._get_cache_path(cache_key, api_name)
        
        if not cache_path.exists():
            logger.debug(f"Cache MISS: {api_name} - {request_params}")
            return None
        
        try:
            # Read cache file
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            # Check if expired
            cached_at = datetime.fromisoformat(cache_data['cached_at'])
            ttl = self.ttl_config.get(api_name, timedelta(hours=1))
            
            if datetime.utcnow() - cached_at > ttl:
                logger.debug(f"Cache EXPIRED: {api_name} - {request_params}")
                # Remove expired cache
                cache_path.unlink()
                return None
            
            logger.info(f"Cache HIT: {api_name} - cached {(datetime.utcnow() - cached_at).seconds}s ago")
            return cache_data['response']
            
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None
    
    async def set(
        self,
        api_name: str,
        request_params: Dict[str, Any],
        response_data: Any
    ) -> None:
        """
        Store API response in cache.
        
        Args:
            api_name: Name of the API
            request_params: Request parameters
            response_data: Response data to cache
        """
        cache_key = self._get_cache_key(api_name, request_params)
        cache_path = self._get_cache_path(cache_key, api_name)
        
        try:
            cache_entry = {
                'api_name': api_name,
                'request_params': request_params,
                'response': response_data,
                'cached_at': datetime.utcnow().isoformat(),
            }
            
            # Write to temp file first, then atomic rename
            temp_path = cache_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(cache_entry, f, indent=2)
            
            temp_path.replace(cache_path)
            logger.debug(f"Cache STORED: {api_name} - {cache_key}")
            
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    async def invalidate(
        self,
        api_name: str,
        request_params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Invalidate cache entries.
        
        Args:
            api_name: Name of the API
            request_params: Specific params to invalidate, or None for all
        """
        if request_params:
            # Invalidate specific entry
            cache_key = self._get_cache_key(api_name, request_params)
            cache_path = self._get_cache_path(cache_key, api_name)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cache INVALIDATED: {api_name} - {request_params}")
        else:
            # Invalidate all entries for API
            api_dir = self.cache_dir / api_name
            if api_dir.exists():
                for cache_file in api_dir.glob("*.json"):
                    cache_file.unlink()
                logger.info(f"Cache CLEARED: {api_name} - all entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats per API
        """
        stats = {}
        
        for api_name in self.ttl_config.keys():
            api_dir = self.cache_dir / api_name
            if api_dir.exists():
                cache_files = list(api_dir.glob("*.json"))
                stats[api_name] = {
                    'total_entries': len(cache_files),
                    'cache_dir': str(api_dir),
                }
        
        return stats


# Global cache instance
api_cache = APICache()

