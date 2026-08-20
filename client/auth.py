"""Client-side HMAC authentication for MCP requests."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from mcp.client._transport import TransportStreams
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

load_dotenv()

HMAC_SECRET = os.environ.get("SECRET", "")
HMAC_TIMESTAMP_HEADER = "X-HMAC-Timestamp"
HMAC_SIGNATURE_HEADER = "X-HMAC-Signature"
HMAC_MAX_AGE_SECONDS = 300  # 5 minutes


def _get_secret() -> bytes:
    if not HMAC_SECRET:
        raise RuntimeError(
            "SECRET not found in environment. "
            "Set it in a .env file or as an environment variable."
        )
    return HMAC_SECRET.encode()


def compute_hmac(body: bytes, timestamp: str) -> str:
    message = timestamp.encode() + b":" + body
    return hmac.new(_get_secret(), message, hashlib.sha256).hexdigest()


def _signing_auth(request: httpx.Request) -> httpx.Request:
    timestamp = str(int(time.time()))
    body = request.content or b""
    signature = compute_hmac(body, timestamp)
    request.headers[HMAC_TIMESTAMP_HEADER] = timestamp
    request.headers[HMAC_SIGNATURE_HEADER] = signature
    return request


@asynccontextmanager
async def HMACTransport(url: str) -> AsyncGenerator[TransportStreams, None]:
    """MCP Transport that signs every HTTP request with HMAC authentication.

    Usage:
        async with Client(HMACTransport("http://...")) as client:
            ...
    """
    client = create_mcp_http_client(auth=_signing_auth)
    async with streamable_http_client(url, http_client=client) as streams:
        yield streams
