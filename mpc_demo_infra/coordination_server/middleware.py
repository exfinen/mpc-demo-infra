from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List
from .config import settings

class IPFilterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        if client_ip not in settings.allowed_ips:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})
        response = await call_next(request)
        return response

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key not in settings.api_keys:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})
        response = await call_next(request)
        return response
