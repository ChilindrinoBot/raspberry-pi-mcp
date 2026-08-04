from __future__ import annotations

import base64
import binascii
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Final

from .. import mcp
from ..audio.manager import audio_manager

MAX_AUDIO_BYTES: Final[int] = 10 * 1024 * 1024

# PIDs of ffplay processes started by this server instance.
# The server is a long-running process, so this set survives between client calls.
_STARTED_PIDS: set[int] = audio_manager._started_pids


def register_process(pid: int) -> None:
    """Registers a PID to be managed by the server."""
    audio_manager.register_process(pid)


def unregister_process(pid: int) -> None:
    """Unregisters a PID."""
    audio_manager.unregister_process(pid)


def _decode_audio_payload(encoded_audio: str, max_bytes: int = MAX_AUDIO_BYTES) -> bytes:
    """Decode a base64-encoded audio payload and enforce a size limit."""
    try:
        decoded = base64.b64decode(encoded_audio, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid base64 audio payload.") from exc

    if len(decoded) > max_bytes:
        raise ValueError(f"Audio payload exceeds the {max_bytes} byte limit.")

    return decoded


def _build_player_command() -> list[str]:
    """Select ffplay to decode and play any audio format via stdin."""
    player = shutil.which("ffplay")
    if player:
        return [player, "-nodisp", "-autoexit", "-"]

    raise RuntimeError("ffplay is not installed. Please run: sudo apt install ffmpeg")


def _is_ffplay_running() -> bool:
    """Return True if any ffplay process started by this server is still alive."""
    return audio_manager.is_ffplay_running()


def _play_audio_bytes_async(audio_bytes: bytes) -> None:
    """Play audio bytes in the background without blocking."""
    command = _build_player_command()
    env = os.environ.copy()
    env.setdefault("PULSE_RUNTIME_PATH", "/run/user/1000/pulse")

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )
    if process.stdin:
        process.stdin.write(audio_bytes)
        process.stdin.close()
    audio_manager.register_process(process.pid, process)


def play_audio_file(file_path: str) -> dict[str, str]:
    """Play an audio file from a local path on the server. Returns busy if audio is already playing."""
    if audio_manager.is_ffplay_running():
        return {
            "status": "busy",
            "message": "The system is busy. Audio is currently playing on the Raspberry Pi.",
        }

    path = Path(file_path)
    if not path.exists():
        return {
            "status": "error",
            "message": f"Audio file not found: {file_path}",
        }

    try:
        audio_manager.start_process(["ffplay", "-nodisp", "-autoexit", str(path)])
        return {
            "status": "playing",
            "message": f"Playback of {path.name} has started successfully.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Failed to start playback: {exc}",
        }


@mcp.tool()
def play_audio(encoded_audio: str) -> dict[str, str]:
    """Decode and play audio. If an audio is already playing system-wide, returns a busy status."""
    if _is_ffplay_running():
        return {
            "status": "busy",
            "message": "The system is busy. Audio is currently playing on the Raspberry Pi.",
        }

    audio_bytes = _decode_audio_payload(encoded_audio)

    try:
        _play_audio_bytes_async(audio_bytes)
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc

    return {
        "status": "playing",
        "message": "Playback has started successfully.",
    }


@mcp.tool()
def stop_audio() -> dict[str, str]:
    """Stop all audio playbacks started by this server."""
    if not _is_ffplay_running():
        return {"status": "stopped", "message": "There is no active audio to stop."}

    errors = audio_manager.stop_all()
    if errors:
        return {"status": "stopped", "message": f"Stopped with warnings: {'; '.join(errors)}"}
    return {"status": "stopped", "message": "All active audio playbacks have been stopped."}