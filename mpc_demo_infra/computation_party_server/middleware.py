from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from .config import settings
from .routes import SHARE_DATA_ENDPOINT, QUERY_COMPUTATION_ENDPOINT

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from .config import settings

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only check API key for specific endpoints
        if request.url.path in [SHARE_DATA_ENDPOINT, QUERY_COMPUTATION_ENDPOINT]:
            api_key = request.headers.get("X-API-Key")
            if api_key != settings.party_api_key:
                raise HTTPException(status_code=403, detail="Invalid API key")
        return await call_next(request)
