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
