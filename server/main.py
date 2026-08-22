from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn

from server import mcp
from server.auth_middleware import AuthMiddleware

__all__ = ["mcp"]

if __name__ == "__main__":
    app = mcp.streamable_http_app(streamable_http_path="/mcp")
    app.add_middleware(AuthMiddleware)
    uvicorn.run(app, host="0.0.0.0", port=7777)
