"""X (Twitter) API v2 client for fetching influencer tweets."""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .config import settings
from .http_client import http_client
from .logging import logger
from .api_cache import api_cache


class XAPIClient:
    """
    X (Twitter) API v2 client for fetching user tweets.
    
    Docs: https://developer.twitter.com/en/docs/twitter-api/tweets/timelines/api-reference
    """
    
    def __init__(self):
        """Initialize X API client with bearer token."""
        self.bearer_token = settings.x_api_bearer_token
        self.base_url = "https://api.twitter.com/2"
        
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for X API requests."""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }
    
    async def get_user_id_by_username(self, username: str) -> Optional[str]:
        """
        Get user ID from username.
        
        Args:
            username: X username (without @)
            
        Returns:
            User ID string or None if not found
        """
        # Check cache first
        cache_key = {'username': username}
        cached_user_id = await api_cache.get('x_api', cache_key)
        
        if cached_user_id:
            logger.info(f"Cache HIT: User ID for @{username}")
            return cached_user_id
        
        try:
            url = f"{self.base_url}/users/by/username/{username}"
            response = await http_client.get(url, headers=self._get_headers())
            data = response.json()
            
            if "data" in data and "id" in data["data"]:
                user_id = data["data"]["id"]
                # Cache user ID (rarely changes)
                await api_cache.set('x_api', cache_key, user_id)
                logger.info(f"Fetched user ID for @{username}: {user_id}")
                return user_id
            else:
                logger.error(f"User @{username} not found: {data}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching user ID for @{username}: {e}")
            return None
    
    async def get_user_tweets(
        self,
        username: str,
        max_results: int = 10,
        since_hours: int = 168,  # 7 days default
        start_time: Optional[str] = None,  # ISO 8601 format or None
        end_time: Optional[str] = None  # ISO 8601 format or None
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent tweets for a user.
        
        Args:
            username: X username (without @)
            max_results: Maximum number of tweets to fetch (5-100)
            since_hours: Only fetch tweets from last N hours (ignored if start_time provided)
            start_time: Optional ISO 8601 datetime string (e.g., "2024-07-01T00:00:00Z")
            end_time: Optional ISO 8601 datetime string (e.g., "2024-09-30T23:59:59Z")
            
        Returns:
            List of tweet dicts with id, text, created_at fields
        """
        # Get user ID first
        user_id = await self.get_user_id_by_username(username)
        if not user_id:
            logger.warning(f"Cannot fetch tweets: user @{username} not found")
            return []
        
        # Calculate start_time if not provided (X API requires ISO 8601 format)
        if start_time is None:
            start_time = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat() + "Z"
        
        # Check cache
        cache_key = {
            'user_id': user_id,
            'max_results': max_results,
            'start_time': start_time[:10] if start_time else None,  # Cache by date only
            'end_time': end_time[:10] if end_time else None
        }
        cached_tweets = await api_cache.get('x_api', cache_key)
        
        if cached_tweets:
            logger.info(f"Cache HIT: Tweets for @{username} ({len(cached_tweets)} tweets)")
            return cached_tweets
        
        try:
            url = f"{self.base_url}/users/{user_id}/tweets"
            params = {
                "max_results": min(max_results, 100),  # X API max is 100
                "start_time": start_time,
                "tweet.fields": "created_at,text,id",
                "exclude": "retweets,replies"  # Focus on original tweets only
            }
            
            # Add end_time if provided (for historical data queries)
            if end_time:
                params["end_time"] = end_time
            
            response = await http_client.get(
                url,
                headers=self._get_headers(),
                params=params
            )
            data = response.json()
            
            if "data" not in data:
                # No tweets found or API error
                error_msg = data.get("detail", data.get("title", "Unknown error"))
                logger.warning(f"No tweets found for @{username}: {error_msg}")
                return []
            
            tweets = []
            for tweet_data in data["data"]:
                tweet = {
                    "id": tweet_data["id"],
                    "text": tweet_data["text"],
                    "created_at": datetime.fromisoformat(
                        tweet_data["created_at"].replace("Z", "+00:00")
                    ),
                    "author_username": username,
                }
                tweets.append(tweet)
            
            # Cache the results
            await api_cache.set('x_api', cache_key, tweets)
            
            logger.info(f"Fetched {len(tweets)} tweets for @{username} (since {start_time[:10]})")
            return tweets
            
        except Exception as e:
            logger.error(f"Error fetching tweets for @{username}: {e}")
            return []
    
    async def get_tweets_for_influencers(
        self,
        usernames: List[str],
        max_results_per_user: int = 10,
        since_hours: int = 168
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch recent tweets for multiple influencers.
        
        Args:
            usernames: List of X usernames (without @)
            max_results_per_user: Max tweets per user
            since_hours: Only fetch tweets from last N hours
            
        Returns:
            Dict mapping username -> list of tweets
        """
        results = {}
        
        for username in usernames:
            tweets = await self.get_user_tweets(
                username=username,
                max_results=max_results_per_user,
                since_hours=since_hours
            )
            results[username] = tweets
            logger.info(f"Fetched {len(tweets)} tweets for @{username}")
        
        total_tweets = sum(len(tweets) for tweets in results.values())
        logger.info(f"Total tweets fetched: {total_tweets} across {len(usernames)} influencers")
        
        return results


# Global X API client instance
x_api_client = XAPIClient()

