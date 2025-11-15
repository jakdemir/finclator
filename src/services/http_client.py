"""HTTP client utilities for external API calls."""
import httpx
from typing import Optional


class HTTPClient:
    """Shared HTTP client with retry logic and standard settings."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Initialize HTTP client.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client instance."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """
        Execute GET request with retry logic.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for httpx.get
            
        Returns:
            HTTP response
        """
        client = await self.get_client()
        
        for attempt in range(self.max_retries):
            try:
                response = await client.get(url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.HTTPError, httpx.RequestError) as e:
                if attempt == self.max_retries - 1:
                    raise
                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** attempt)
        
        raise RuntimeError("Unexpected retry logic failure")
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """
        Execute POST request with retry logic.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for httpx.post
            
        Returns:
            HTTP response
        """
        client = await self.get_client()
        
        for attempt in range(self.max_retries):
            try:
                response = await client.post(url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.HTTPError, httpx.RequestError) as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        raise RuntimeError("Unexpected retry logic failure")


# Global HTTP client instance
http_client = HTTPClient()


import asyncio

