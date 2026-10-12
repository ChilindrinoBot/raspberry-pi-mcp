from __future__ import annotations

import threading
import time
from pathlib import Path

from .. import config
from .. import http
from .. import images
from .. import state


def _list_special_gifs(routine: str) -> list[Path]:
    """List gif files for a given special routine (sorted)."""
    routine_dir = config.SPECIAL_GIF_ROOT / routine
    if not routine_dir.is_dir():
        return []
    return sorted(
        p for p in routine_dir.iterdir() if p.is_file() and p.suffix.lower() == ".gif"
    )


def _list_special_routines() -> list[str]:
    """List available special routines (subdirectories under SPECIAL_GIF_ROOT)."""
    if not config.SPECIAL_GIF_ROOT.is_dir():
        return []
    return sorted(p.name for p in config.SPECIAL_GIF_ROOT.iterdir() if p.is_dir())


def _pato_gira_status_lines(gifs: list[str], interval: int | None) -> list[str]:
    """Detail lines for cube://special when a pato-gira-style routine runs."""
    return [f"Gifs: {', '.join(gifs)} (switch every {interval}s)"]


def _special_loop(seconds: int, gifs: list[str]) -> None:
    """Continuously switch between the uploaded special gifs every `seconds`.

    Simple timer sin restricciones: solo duerme `seconds` y cambia gif.
    Corre en background thread tras start_special_routine. Usa sleep
    interrumpible por 1s para responder rapido a stop.
    """
    if not gifs:
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return
    try:
        with state._SPECIAL_MODE_LOCK:
            current = state._SPECIAL_CURRENT_GIF
        idx = gifs.index(current) if current in gifs else 0
    except ValueError:
        idx = 0
    try:
        while state._is_special_mode_running():
            # simple timer: sleep seconds en pasos de 1s para parar rapido
            for _ in range(seconds):
                if not state._is_special_mode_running():
                    break
                time.sleep(1)
            if not state._is_special_mode_running():
                break
            idx = (idx + 1) % len(gifs)
            next_gif = gifs[idx]
            try:
                response = http._set_cube_gif(next_gif)
                if "FAIL" in response.upper():
                    continue
                with state._SPECIAL_MODE_LOCK:
                    state._SPECIAL_CURRENT_GIF = next_gif
            except Exception:
                continue
    finally:
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False


def _start_special_pato_gira(routine: str, seconds: int) -> dict[str, str]:
    """Alternating flow for pato-gira-style special routines.

    Clears the Cube, uploads every gif from media/special/gifs/<routine> (e.g.
    pato-gira.gif and pato-gira-rev.gif) and alternates between them every
    `seconds` in a background thread. Any routine directory works, so future
    alternating routines reuse this flow until they get their own module.
    Runs on the unified special state; starting it requires the mode to be
    stopped.
    """
    # Validate routine exists and has gifs
    routine_dir = config.SPECIAL_GIF_ROOT / routine
    if not routine_dir.is_dir():
        available = ", ".join(_list_special_routines()) or "none"
        return {"status": "error", "message": f"Routine not found: {routine}. Available: {available}."}

    gif_paths = _list_special_gifs(routine)
    if not gif_paths:
        return {"status": "error", "message": f"No .gif files found for routine {routine} in {routine_dir}."}

    # Sort to ensure deterministic order: pato-gira.gif before pato-gira-rev.gif
    # (alphabetical puts rev first because '-' < '.'), so sort with rev last.
    gif_paths = sorted(gif_paths, key=lambda p: ("rev" in p.name.lower(), p.name.lower()))
    gif_names = [p.name for p in gif_paths]

    # Validate dimensions upfront
    for p in gif_paths:
        dims = images._image_dimensions(p.read_bytes())
        if dims != config.IMAGE_REQUIRED_DIMENSIONS:
            w, h = dims if dims else (0, 0)
            return {
                "status": "error",
                "message": f"Gif must be {config.IMAGE_REQUIRED_DIMENSIONS[0]}x{config.IMAGE_REQUIRED_DIMENSIONS[1]} (got {w}x{h}): {p.name}.",
            }

    clamped = max(config.SPECIAL_MIN_SECONDS, min(config.SPECIAL_MAX_SECONDS, seconds))

    with state._SPECIAL_MODE_LOCK:
        if state._SPECIAL_MODE_RUNNING:
            return {
                "status": "error",
                "message": "Special routine is already running. Call stop_special_routine first.",
            }
        state._SPECIAL_MODE_RUNNING = True
        state._SPECIAL_MODE_SUSPENDED = False

    # Stop competing modes before we start clearing/uploading
    was_random, _prev_r = state._stop_random_mode()
    was_image, _prev_i = state._stop_image_mode()

    # Clear cube memory
    try:
        files_before = http._fetch_cube_files()
    except Exception as e:
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {"status": "error", "message": f"Failed to fetch contents from Cube: {e}"}

    if files_before:
        try:
            http._clear_cube_contents_request()
        except Exception as e:
            with state._SPECIAL_MODE_LOCK:
                state._SPECIAL_MODE_RUNNING = False
            return {"status": "error", "message": f"Failed to clear Cube contents: {e}"}
        # Verify empty (up to 3 attempts)
        cleared = False
        for _ in range(3):
            try:
                remaining = http._fetch_cube_files()
            except Exception as e:
                with state._SPECIAL_MODE_LOCK:
                    state._SPECIAL_MODE_RUNNING = False
                return {"status": "error", "message": f"Failed to verify clear on Cube: {e}"}
            if not remaining:
                cleared = True
                break
            time.sleep(1)
        if not cleared:
            with state._SPECIAL_MODE_LOCK:
                state._SPECIAL_MODE_RUNNING = False
            return {"status": "error", "message": "Clear could not be confirmed: the Cube still lists files."}

    # Upload each gif in the routine (check free space before each) - simple sin restricciones
    for path in gif_paths:
        payload = path.read_bytes()
        rejection = images._cube_free_space_rejection(len(payload))
        if rejection:
            with state._SPECIAL_MODE_LOCK:
                state._SPECIAL_MODE_RUNNING = False
            return {"status": "error", "message": rejection}
        try:
            http._upload_cube_image(path.name, payload)
        except Exception as e:
            with state._SPECIAL_MODE_LOCK:
                state._SPECIAL_MODE_RUNNING = False
            return {"status": "error", "message": f"Failed to upload {path.name} to Cube: {e}"}
        try:
            available = http._fetch_cube_gifs()
        except Exception as e:
            with state._SPECIAL_MODE_LOCK:
                state._SPECIAL_MODE_RUNNING = False
            return {"status": "error", "message": f"Failed to verify upload of {path.name} on Cube: {e}"}
        if not images._is_in_cube_filelist(path.name, available):
            with state._SPECIAL_MODE_LOCK:
                state._SPECIAL_MODE_RUNNING = False
            return {
                "status": "error",
                "message": f"Upload could not be confirmed: {path.name} is not in the Cube file list.",
            }

    first_gif = gif_names[0]
    try:
        response = http._set_cube_gif(first_gif)
    except Exception as e:
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {"status": "error", "message": f"Failed to set gif {first_gif} on Cube: {e}"}
    if "FAIL" in response.upper():
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {"status": "error", "message": f"Cube refused to set gif {first_gif}. Response: {response}"}

    with state._SPECIAL_MODE_LOCK:
        state._SPECIAL_CURRENT_GIF = first_gif
        state._SPECIAL_CURRENT_ROUTINE = routine
        state._SPECIAL_GIFS = gif_names
        state._SPECIAL_INTERVAL = clamped

    threading.Thread(target=_special_loop, args=(clamped, gif_names), daemon=True).start()

    parts = [f"Special routine '{routine}' started: {first_gif} displayed; switching every {clamped}s between {', '.join(gif_names)}."]
    if was_random:
        parts.append("Random gif mode stopped.")
    if was_image:
        parts.append("Random image mode stopped.")
    if response:
        parts.append(f"Device response: {response}")
    return {"status": "success", "message": " ".join(parts)}
