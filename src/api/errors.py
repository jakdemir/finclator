"""Custom error handling for the API."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with clear messages."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append({
            "field": field,
            "message": message,
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )


def validate_asset(asset: str) -> str:
    """Validate asset symbol."""
    asset_upper = asset.upper()
    if asset_upper not in ["BTC", "GOLD", "SPX"]:
        valid_assets = ", ".join(["BTC", "GOLD", "SPX"])
        raise ValueError(
            f"Invalid asset '{asset}'. Must be one of: {valid_assets}"
        )
    return asset_upper


def validate_horizon(horizon: str) -> str:
    """Validate time horizon."""
    horizon_upper = horizon.upper()
    if horizon_upper not in ["SHORT", "MEDIUM", "LONG"]:
        valid_horizons = ", ".join(["SHORT", "MEDIUM", "LONG"])
        raise ValueError(
            f"Invalid horizon '{horizon}'. Must be one of: {valid_horizons}"
        )
    return horizon_upper


class InfluencerNotFoundError(Exception):
    """Raised when an influencer is not found."""
    pass


class SignalNotFoundError(Exception):
    """Raised when a signal is not found."""
    pass

