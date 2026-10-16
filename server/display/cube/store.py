from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Final

from . import config

# Persistent cube state that must survive server restarts (last schedule,
# remembered brightness). A minimal key-value table: one file, no
# dependencies, values JSON-encoded. Failures never raise to callers —
# reads fall back to the default, writes are logged — so a missing or
# broken database can never take the server down.


def _connect() -> sqlite3.Connection:
    db = sqlite3.connect(str(config.STATE_DB_FILE))
    db.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return db


def get_setting(key: str, default: Any = None) -> Any:
    """Return the persisted value for <key>, or <default> when absent/broken."""
    try:
        with _connect() as db:
            row = db.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
    except Exception as e:
        print(f"state store: read failed for {key!r}: {e}")
        return default
    if row is None:
        return default
    try:
        return json.loads(row[0])
    except ValueError:
        return default


def set_setting(key: str, value: Any) -> None:
    """Persist <value> (JSON-encodable) under <key>, creating the database."""
    try:
        payload = json.dumps(value)
    except (TypeError, ValueError) as e:
        print(f"state store: cannot encode {key!r}: {e}")
        return
    try:
        with _connect() as db:
            db.execute("INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)", (key, payload))
    except Exception as e:
        print(f"state store: write failed for {key!r}: {e}")


def delete_setting(key: str) -> None:
    """Remove <key> from the store; missing keys are a no-op."""
    try:
        with _connect() as db:
            db.execute("DELETE FROM kv WHERE key = ?", (key,))
    except Exception as e:
        print(f"state store: delete failed for {key!r}: {e}")


# The single cube_config object: the whole persistent cube state in one row,
# so reads and writes are always whole-object snapshots that cannot end up
# half-written. Persist-only-what-you-can't-re-read: just the schedule hours
# (the firmware exposes nothing). Brightness is never stored — the live
# level is always re-readable from the Cube itself, which persists it on its
# own side too.
_CONFIG_KEY: Final[str] = "cube_config"
_CONFIG_LOCK: Final[threading.Lock] = threading.Lock()


def _default_config() -> dict[str, Any]:
    return {"schedule": None}


def _slim_schedule(raw: Any) -> dict[str, Any] | None:
    """Keep only hours + switch from a stored schedule dict."""
    if not isinstance(raw, dict):
        return None
    try:
        return {
            "time1": str(raw["time1"]),
            "time2": str(raw["time2"]),
            "enabled": bool(raw["enabled"]),
        }
    except KeyError:
        return None


def get_cube_config() -> dict[str, Any]:
    """Return the whole persistent cube config (hours only, normalized)."""
    stored = get_setting(_CONFIG_KEY)
    schedule: dict[str, Any] | None = None
    if isinstance(stored, dict):
        schedule = _slim_schedule(stored.get("schedule"))
    return {"schedule": schedule}


def update_cube_config(**kwargs: Any) -> dict[str, Any]:
    """Merge <kwargs> into the cube config and persist it atomically.

    The lock makes read-modify-write safe: two tools writing at once cannot
    interleave and lose each other's fields.
    """
    with _CONFIG_LOCK:
        config = get_cube_config()
        config.update(kwargs)
        set_setting(_CONFIG_KEY, config)
        return config
