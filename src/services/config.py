"""Configuration management for Finclator."""
import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql+asyncpg://localhost/finclator"
    
    # External API keys
    x_api_bearer_token: Optional[str] = None
    alphavantage_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # Sentiment model configuration
    sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"  # Twitter-specific sentiment model
    use_agent_sentiment: bool = True  # Use agent-based (OpenAI) instead of HuggingFace
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Logging
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='ignore',  # Allow extra fields in .env without errors
    )


# Global settings instance
settings = Settings()

