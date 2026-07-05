from __future__ import annotations

import base64
import binascii
import os
import shutil
import subprocess
import time
from typing import Final

from .. import mcp

MAX_AUDIO_BYTES: Final[int] = 10 * 1024 * 1024
_ACTIVE_PLAYER_PROCESS: subprocess.Popen[bytes] | None = None


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
    """Check system-wide if an instance of ffplay is currently active."""
    try:
        # Usamos un comando nativo de Linux muy rápido para ver si ffplay está en ejecución
        # Si pgrep encuentra el proceso, devuelve 0 (True). Si no, devuelve un error (False).
        subprocess.check_output(["pgrep", "-x", "ffplay"])
        return True
    except subprocess.CalledProcessError:
        return False


def _play_audio_bytes_async(audio_bytes: bytes) -> None:
    """Play audio bytes in the background without blocking."""
    global _ACTIVE_PLAYER_PROCESS

    command = _build_player_command()
    env = os.environ.copy()
    env.setdefault("PULSE_RUNTIME_PATH", "/run/user/1000/pulse")

    _ACTIVE_PLAYER_PROCESS = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )

    try:
        _ACTIVE_PLAYER_PROCESS.stdin.write(audio_bytes)
        _ACTIVE_PLAYER_PROCESS.stdin.close()
        
        # Una pequeña pausa para que el proceso se registre en el sistema operativo
        time.sleep(0.1)

    except Exception as exc:
        if _ACTIVE_PLAYER_PROCESS:
            try:
                _ACTIVE_PLAYER_PROCESS.kill()
            except Exception:
                pass
        _ACTIVE_PLAYER_PROCESS = None
        raise RuntimeError(f"Error al transmitir datos al reproductor: {exc}") from exc


@mcp.tool()
def play_audio(encoded_audio: str) -> dict[str, str]:
    """Decode and play audio. If an audio is already playing system-wide, returns a busy status."""
    
    # NUEVA VERIFICACIÓN REAL: Le preguntamos al sistema si ffplay ya está corriendo
    if _is_ffplay_running():
        return {
            "status": "busy",
            "message": "The system is busy. Audio is currently playing on the Raspberry Pi."
        }

    audio_bytes = _decode_audio_payload(encoded_audio)

    try:
        _play_audio_bytes_async(audio_bytes)
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc

    return {
        "status": "playing",
        "message": "Playback has started successfully."
    }


@mcp.tool()
def stop_audio() -> dict[str, str]:
    """Stop all active audio playbacks system-wide."""
    global _ACTIVE_PLAYER_PROCESS

    if not _is_ffplay_running():
        _ACTIVE_PLAYER_PROCESS = None
        return {"status": "stopped", "message": "There is no active audio to stop."}

    # Si tenemos la referencia del proceso local, intentamos cerrarlo amigablemente
    if _ACTIVE_PLAYER_PROCESS and _ACTIVE_PLAYER_PROCESS.poll() is None:
        _ACTIVE_PLAYER_PROCESS.terminate()
        try:
            _ACTIVE_PLAYER_PROCESS.wait(timeout=1)
        except subprocess.TimeoutExpired:
            _ACTIVE_PLAYER_PROCESS.kill()
    
    # Por si acaso hubiera otro proceso ffplay huérfano o paralelo, lo matamos a nivel sistema
    try:
        subprocess.run(["pkill", "-x", "ffplay"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    _ACTIVE_PLAYER_PROCESS = None
    return {"status": "stopped", "message": "All active audio playbacks have been stopped."}