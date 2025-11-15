"""FastAPI dependencies for database sessions and configuration."""
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.services.config import settings


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async for session in get_db():
        yield session


def get_settings():
    """
    Dependency to get application settings.
    
    Returns:
        Settings object
    """
    return settings

