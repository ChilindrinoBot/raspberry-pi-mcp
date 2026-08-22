"""Client-side Bearer token authentication for MCP requests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from mcp.client._transport import TransportStreams
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

load_dotenv()

AUTH_TOKEN = os.environ.get("SECRET", "")


def _bearer_auth(request: httpx.Request) -> httpx.Request:
    request.headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    return request


@asynccontextmanager
async def AuthTransport(url: str) -> AsyncGenerator[TransportStreams, None]:
    """MCP Transport that sends every HTTP request with Bearer authentication.

    Usage:
        async with Client(AuthTransport("http://...")) as client:
            ...
    """
    client = create_mcp_http_client(auth=_bearer_auth)
    async with streamable_http_client(url, http_client=client) as streams:
        yield streams
