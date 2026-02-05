"""API dependencies"""
from fastapi import Header, HTTPException, WebSocket, status

from app.config import settings


def require_api_key(x_api_key: str = Header(None)) -> None:
    """Validate API key for HTTP requests."""
    if not settings.API_KEY:
        return  # API_KEY not configured - skip auth (dev mode)
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )


async def require_ws_api_key(websocket: WebSocket) -> bool:
    """Validate API key for WebSocket requests."""
    if not settings.API_KEY:
        return True  # API_KEY not configured - skip auth (dev mode)
    api_key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")
    if api_key != settings.API_KEY:
        await websocket.close(code=1008)
        return False
    return True
