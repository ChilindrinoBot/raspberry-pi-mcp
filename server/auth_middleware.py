"""Simple Bearer token authentication middleware."""

from __future__ import annotations

import hmac
import os

from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

load_dotenv()

AUTH_TOKEN = os.environ.get("SECRET", "")
EXPECTED_AUTHORIZATION = f"Bearer {AUTH_TOKEN}"


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        auth = request.headers.get("Authorization", "")
        if not AUTH_TOKEN or not hmac.compare_digest(auth, EXPECTED_AUTHORIZATION):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)
