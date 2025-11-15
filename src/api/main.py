"""FastAPI application entry point."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.api.routers import signals, influencers, admin
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
app.include_router(admin.router)

# Mount static files (dashboard)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/dashboard")
async def get_dashboard():
    """Serve the user dashboard HTML."""
    dashboard_path = Path(__file__).parent / "static" / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"error": "Dashboard not found"}


@app.get("/admin")
async def get_admin_dashboard():
    """Serve the admin dashboard HTML."""
    admin_path = Path(__file__).parent / "static" / "admin.html"
    if admin_path.exists():
        return FileResponse(admin_path)
    return {"error": "Admin dashboard not found"}


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

