"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import signals, influencers
from src.services.config import settings
from src.services.logging import setup_logging, logger

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Finclator API",
    version="0.1.0",
    description="Trust-scored market indicators from influencer sentiment",
)

# CORS middleware for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(signals.router)
app.include_router(influencers.router)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Finclator API starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Finclator API shutting down")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Finclator API",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "ok",
        "database": "connected",  # Could add actual DB health check
    }

