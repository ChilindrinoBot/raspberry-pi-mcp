"""Server-side HMAC authentication middleware for ASGI."""

from __future__ import annotations

import hashlib
import hmac
import os
import time

from dotenv import load_dotenv
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

load_dotenv()

HMAC_SECRET = os.environ.get("SECRET", "")
HMAC_TIMESTAMP_HEADER = "X-HMAC-Timestamp"
HMAC_SIGNATURE_HEADER = "X-HMAC-Signature"
HMAC_MAX_AGE_SECONDS = 60  # 1 minute


def _get_secret() -> bytes:
    if not HMAC_SECRET:
        raise RuntimeError(
            "SECRET not found in environment. "
            "Set it in a .env file or as an environment variable."
        )
    return HMAC_SECRET.encode()


def compute_hmac(body: bytes, timestamp: str) -> str:
    # Concatenación directa en bytes para evitar errores de codificación UTF-8
    message = timestamp.encode() + b":" + body
    return hmac.new(_get_secret(), message, hashlib.sha256).hexdigest()


class HMACMiddleware:
    """ASGI middleware that validates HMAC-SHA256 authentication headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        timestamp = request.headers.get(HMAC_TIMESTAMP_HEADER)
        signature = request.headers.get(HMAC_SIGNATURE_HEADER)

        if not timestamp or not signature:
            response = JSONResponse(
                {"error": "Missing HMAC authentication headers"},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        try:
            req_timestamp = int(timestamp)
            now = int(time.time())
            request_age = now - req_timestamp
        except ValueError:
            response = JSONResponse(
                {"error": "Invalid timestamp format"},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        if request_age > HMAC_MAX_AGE_SECONDS or request_age < -30:
            response = JSONResponse(
                {"error": "Request timestamp out of acceptable range"},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        try:
            body = await request.body()
            expected = compute_hmac(body, timestamp)
        except Exception:
            response = JSONResponse(
                {"error": "Error processing request body"},
                status_code=400,
            )
            await response(scope, receive, send)
            return

        if not hmac.compare_digest(expected, signature):
            response = JSONResponse(
                {"error": "Invalid HMAC signature"},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        # Re-injects the correctly read body ONLY ONCE and then
        # delegates to the original `receive`, allowing the framework to
        # observe `http.disconnect` and close the connection cleanly.
        #
        # If we always returned the same dict, loops like
        # `while (await receive()).get("type") != "http.disconnect": pass`
        # used by the MCP library would loop indefinitely (a 100% CPU
        # spin-loop that also freezes the event loop and blocks SIGINT).
        body_delivered = False

        async def receive_replay():
            nonlocal body_delivered
            if not body_delivered:
                body_delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, receive_replay, send)