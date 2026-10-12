from __future__ import annotations

import random
import threading
import time
from pathlib import Path
from typing import Final

from .. import config
from .. import http
from .. import images
from .. import state

# Directory layout:
#   media/special/gifs/oiia/oiia.gif          default gif, always on screen
#   media/special/gifs/oiia/random/*.gif      pool of random interruption gifs
# Oiia runs on the unified special state (see ..state): _SPECIAL_GIFS holds
# the preloaded random batch, _SPECIAL_INTERVAL is `every`,
# _SPECIAL_OIIA_DURATION/_SPECIAL_OIIA_RENEW the remaining timers.
OIIA_DIR: Final[Path] = config.SPECIAL_GIF_ROOT / "oiia"
OIIA_DEFAULT_GIF_NAME: Final[str] = "oiia.gif"
OIIA_RANDOM_DIR: Final[Path] = OIIA_DIR / "random"


def _oiia_status_lines(
    gifs: list[str] | None, interval: int | None, duration: int | None, renew: int | None
) -> list[str]:
    """Detail lines for cube://special when the running routine is oiia.

    Convention for future special modes: implement `<mode>_status_lines(...)`
    in the mode module and call it from the status branch in core.py.
    """
    lines = [f"Default gif: {OIIA_DEFAULT_GIF_NAME}"]
    renew_note = f", renew every {renew}s" if renew else ", auto-renew disabled"
    if gifs:
        lines.append(
            f"Randoms ({len(gifs)} preloaded): {', '.join(gifs)} "
            f"(random pick every {interval}s for {duration}s each{renew_note})"
        )
    else:
        lines.append(f"No random gifs preloaded ({renew_note}).")
    return lines


def _list_oiia_random_gifs() -> list[Path]:
    """List the .gif files in the oiia random pool (sorted)."""
    if not OIIA_RANDOM_DIR.is_dir():
        return []
    return sorted(
        p for p in OIIA_RANDOM_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".gif"
    )


def _oiia_fill_randoms(prefer_exclude: set[str] | None = None) -> list[str]:
    """Upload random oiia gifs to the Cube until no more fit.

    Gifs are picked from media/special/gifs/oiia/random in random order;
    names in `prefer_exclude` (usually the previous batch) are tried last so
    refills bring fresh gifs when the pool is bigger than the Cube memory.
    Uploading only writes to flash and never changes the displayed gif, so the
    default gif stays on screen while this runs. Gifs that would break the
    free-space reserve are skipped so smaller ones still pack the memory;
    only a free-space check failure aborts the fill. Returns the uploaded
    names in order.
    """
    pool = _list_oiia_random_gifs()
    random.shuffle(pool)
    if prefer_exclude:
        pool = [p for p in pool if p.name not in prefer_exclude] + [
            p for p in pool if p.name in prefer_exclude
        ]
    uploaded: list[str] = []
    for path in pool:
        if not state._is_special_mode_running():
            break
        try:
            payload = path.read_bytes()
        except Exception:
            continue
        if images._image_dimensions(payload) != config.IMAGE_REQUIRED_DIMENSIONS:
            continue
        rejection = images._cube_free_space_rejection(len(payload))
        if rejection:
            if rejection.startswith("Failed to check free space"):
                break
            continue
        try:
            http._upload_cube_image(path.name, payload)
        except Exception:
            continue
        try:
            available = http._fetch_cube_gifs()
        except Exception:
            continue
        if images._is_in_cube_filelist(path.name, available):
            uploaded.append(path.name)
    return uploaded


def _oiia_refresh_randoms() -> list[str]:
    """Replace the preloaded random batch with a fresh one.

    Must only be called while the default gif is displayed (never in the
    middle of a random gif): old random gifs are deleted from the Cube, then a
    new random batch is uploaded until the memory is full. Returns the new
    batch (possibly empty when nothing could be uploaded).
    """
    with state._SPECIAL_MODE_LOCK:
        old = list(state._SPECIAL_GIFS) if state._SPECIAL_GIFS else []
    for name in old:
        if not state._is_special_mode_running():
            return old
        try:
            http._delete_cube_file(name)
        except Exception:
            continue
    new_batch = _oiia_fill_randoms(prefer_exclude=set(old))
    with state._SPECIAL_MODE_LOCK:
        state._SPECIAL_GIFS = new_batch
    return new_batch


def _oiia_loop(every: int, duration: int, renew: int) -> None:
    """Show the default oiia gif with momentary random interruptions.

    Every `every` seconds a randomly picked preloaded gif is displayed for
    `duration` seconds (repeats allowed), then the default gif is restored.
    Independently, every `renew` seconds (0 disables it) the preloaded batch
    is replaced with fresh random gifs. Refills only run while the default gif
    is on screen, never in the middle of a random gif. Runs in a background
    thread until stop_special_routine is called; state lives in the unified
    special mode.
    """
    last_refresh = time.monotonic()
    try:
        while state._is_special_mode_running():
            state._sleep_interruptible_for_special(every, config.OIIA_DISPLAY_POLL_SECONDS)
            if not state._is_special_mode_running():
                break
            if renew > 0 and time.monotonic() - last_refresh >= renew:
                _oiia_refresh_randoms()
                last_refresh = time.monotonic()
                if not state._is_special_mode_running():
                    break
            with state._SPECIAL_MODE_LOCK:
                gifs = list(state._SPECIAL_GIFS) if state._SPECIAL_GIFS else []
            if not gifs:
                gifs = _oiia_refresh_randoms()
                last_refresh = time.monotonic()
                if not gifs:
                    continue
            next_gif = random.choice(gifs)
            try:
                response = http._set_cube_gif(next_gif)
            except Exception:
                continue
            if "FAIL" in response.upper():
                continue
            with state._SPECIAL_MODE_LOCK:
                state._SPECIAL_CURRENT_GIF = next_gif
            state._sleep_interruptible_for_special(duration, config.OIIA_DISPLAY_POLL_SECONDS)
            if not state._is_special_mode_running():
                break
            try:
                back = http._set_cube_gif(OIIA_DEFAULT_GIF_NAME)
                if "FAIL" not in back.upper():
                    with state._SPECIAL_MODE_LOCK:
                        state._SPECIAL_CURRENT_GIF = OIIA_DEFAULT_GIF_NAME
            except Exception:
                pass
    finally:
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False


def _start_special_oiia(
    every: int = config.OIIA_DEFAULT_EVERY,
    duration: int = config.OIIA_DEFAULT_DURATION,
    renew: int = config.OIIA_DEFAULT_RENEW,
) -> dict[str, str]:
    """
    Oiia flow for start_special_routine(routine="oiia") on unified special state.

    Clears all files from the Cube's memory, uploads the default gif
    media/special/gifs/oiia/oiia.gif (240x240) and displays it, then uploads
    random gifs from media/special/gifs/oiia/random in random order, packing
    smaller ones until no more fit on the device. Every `every` seconds a
    randomly picked preloaded gif is shown for `duration` seconds (repeats
    allowed) and then the default gif is restored. Independently, every
    `renew` seconds the preloaded batch is replaced with fresh random gifs
    while the default stays on screen (uploads/deletes never interrupt the
    display, so refills never happen in the middle of a random gif and never
    overload the device with back-to-back flash I/O).

    Args:
        every: Seconds between random gif appearances
            (default 60, clamped to [10, 3600]).
        duration: Seconds each random gif stays on screen before the default
            gif is restored (default 10, clamped to [3, 600]). Must be less
            than `every`.
        renew: Seconds between preloaded batch renewals
            (default 600 = 10 min, clamped to [0, 86400]). 0 disables
            auto-renew: the initial batch is kept until stopped.
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    clamped_every = max(config.OIIA_MIN_EVERY, min(config.OIIA_MAX_EVERY, every))
    clamped_duration = max(config.OIIA_MIN_DURATION, min(config.OIIA_MAX_DURATION, duration))
    clamped_renew = max(config.OIIA_MIN_RENEW, min(config.OIIA_MAX_RENEW, renew))
    if clamped_duration >= clamped_every:
        return {
            "status": "error",
            "message": f"Invalid timers: duration ({clamped_duration}s) must be less than every ({clamped_every}s).",
        }

    with state._SPECIAL_MODE_LOCK:
        if state._SPECIAL_MODE_RUNNING:
            return {
                "status": "error",
                "message": "Special routine is already running. Call stop_special_routine first.",
            }
        state._SPECIAL_MODE_RUNNING = True
        state._SPECIAL_MODE_SUSPENDED = False

    was_random, _prev_r = state._stop_random_mode()
    was_image, _prev_i = state._stop_image_mode()

    default_path = OIIA_DIR / OIIA_DEFAULT_GIF_NAME
    if not default_path.is_file():
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {"status": "error", "message": f"Default oiia gif not found: {default_path}."}

    try:
        default_payload = default_path.read_bytes()
    except Exception as e:
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {"status": "error", "message": f"Failed to read default oiia gif: {e}"}

    dims = images._image_dimensions(default_payload)
    if dims != config.IMAGE_REQUIRED_DIMENSIONS:
        w, h = dims if dims else (0, 0)
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {
            "status": "error",
            "message": f"Default oiia gif must be {config.IMAGE_REQUIRED_DIMENSIONS[0]}x{config.IMAGE_REQUIRED_DIMENSIONS[1]} (got {w}x{h}).",
        }

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

    rejection = images._cube_free_space_rejection(len(default_payload))
    if rejection:
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {"status": "error", "message": rejection}
    try:
        http._upload_cube_image(OIIA_DEFAULT_GIF_NAME, default_payload)
    except Exception as e:
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {"status": "error", "message": f"Failed to upload {OIIA_DEFAULT_GIF_NAME} to Cube: {e}"}
    try:
        available = http._fetch_cube_gifs()
    except Exception as e:
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {"status": "error", "message": f"Failed to verify upload of {OIIA_DEFAULT_GIF_NAME} on Cube: {e}"}
    if not images._is_in_cube_filelist(OIIA_DEFAULT_GIF_NAME, available):
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {
            "status": "error",
            "message": f"Upload could not be confirmed: {OIIA_DEFAULT_GIF_NAME} is not in the Cube file list.",
        }

    try:
        response = http._set_cube_gif(OIIA_DEFAULT_GIF_NAME)
    except Exception as e:
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {"status": "error", "message": f"Failed to set gif {OIIA_DEFAULT_GIF_NAME} on Cube: {e}"}
    if "FAIL" in response.upper():
        with state._SPECIAL_MODE_LOCK:
            state._SPECIAL_MODE_RUNNING = False
        return {"status": "error", "message": f"Cube refused to set gif {OIIA_DEFAULT_GIF_NAME}. Response: {response}"}

    preloaded = _oiia_fill_randoms()
    if not state._is_special_mode_running():
        return {"status": "error", "message": "Special routine was stopped while preloading random gifs."}

    with state._SPECIAL_MODE_LOCK:
        state._SPECIAL_CURRENT_GIF = OIIA_DEFAULT_GIF_NAME
        state._SPECIAL_CURRENT_ROUTINE = "oiia"
        state._SPECIAL_GIFS = preloaded
        state._SPECIAL_INTERVAL = clamped_every
        state._SPECIAL_OIIA_DURATION = clamped_duration
        state._SPECIAL_OIIA_RENEW = clamped_renew

    threading.Thread(target=_oiia_loop, args=(clamped_every, clamped_duration, clamped_renew), daemon=True).start()

    parts = [
        f"Oiia routine started: {OIIA_DEFAULT_GIF_NAME} displayed; "
        f"a random gif shows every {clamped_every}s for {clamped_duration}s."
    ]
    if preloaded:
        parts.append(f"Preloaded {len(preloaded)} random gif(s): {', '.join(preloaded)}.")
    else:
        parts.append("No random gifs could be preloaded (only the default gif will show).")
    if clamped_renew:
        parts.append(f"Random batch renews every {clamped_renew}s.")
    else:
        parts.append("Auto-renew disabled: the initial batch is kept until stopped.")
    if was_random:
        parts.append("Random gif mode stopped.")
    if was_image:
        parts.append("Random image mode stopped.")
    if response:
        parts.append(f"Device response: {response}")
    return {"status": "success", "message": " ".join(parts)}
