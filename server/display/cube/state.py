from __future__ import annotations

import threading
import time
from typing import Final

from . import config
from . import http

# Temporary gif flow state. While _TEMP_GIF_RUNNING is True a tmp gif is being
# shown and its previous gif has not been restored yet; new temporary shows are
# rejected until it finishes.
_TEMP_GIF_RUNNING: bool = False
_TEMP_GIF_LOCK: Final[threading.Lock] = threading.Lock()

# Random gif mode state. _RANDOM_MODE_RUNNING is True while the background
# loop keeps swapping gifs; _RANDOM_CURRENT_GIF remembers which local gif is
# currently uploaded and displayed as random.gif; _RANDOM_MODE_SUSPENDED is
# True while a temporary gif borrowed the screen, so the loop waits without
# cycling until the previous gif is restored. While the Cube display is off
# (brightness 0 or unreachable) the loop also pauses by itself.
_RANDOM_MODE_RUNNING: bool = False
_RANDOM_MODE_SUSPENDED: bool = False
_RANDOM_CURRENT_GIF: str | None = None
_RANDOM_MODE_LOCK: Final[threading.Lock] = threading.Lock()

# Random image mode state; mirrors the random gif mode state. Both modes share
# one screen, so starting one stops the other and a temporary gif suspends
# whichever mode is active until the previous gif is restored.
_RANDOM_IMAGE_MODE_RUNNING: bool = False
_RANDOM_IMAGE_MODE_SUSPENDED: bool = False
_RANDOM_CURRENT_IMAGE: str | None = None
_RANDOM_IMAGE_MODE_LOCK: Final[threading.Lock] = threading.Lock()

# Special routine mode state (generic routines and oiia share this unified
# mode). For routine="oiia", _SPECIAL_GIFS holds the preloaded random batch,
# _SPECIAL_INTERVAL is `every`, and _SPECIAL_OIIA_DURATION/_SPECIAL_OIIA_RENEW
# hold the remaining oiia timers (generic routines leave them None).
_SPECIAL_MODE_RUNNING: bool = False
_SPECIAL_MODE_SUSPENDED: bool = False
_SPECIAL_CURRENT_GIF: str | None = None
_SPECIAL_CURRENT_ROUTINE: str | None = None
_SPECIAL_GIFS: list[str] | None = None
_SPECIAL_INTERVAL: int | None = None
_SPECIAL_OIIA_DURATION: int | None = None
_SPECIAL_OIIA_RENEW: int | None = None
_SPECIAL_MODE_LOCK: Final[threading.Lock] = threading.Lock()

# Brightness level remembered when the display is turned off, so it can be
# restored on the next power on. None means nothing has been remembered yet.
_REMEMBERED_BRIGHTNESS: int | None = None


def _is_random_mode_running() -> bool:
    with _RANDOM_MODE_LOCK:
        return _RANDOM_MODE_RUNNING


def _is_random_mode_suspended() -> bool:
    with _RANDOM_MODE_LOCK:
        return _RANDOM_MODE_SUSPENDED


def _stop_random_mode() -> tuple[bool, str | None]:
    """Stop the random gif mode entirely. Returns (was_running, current_gif)."""
    global _RANDOM_MODE_RUNNING, _RANDOM_MODE_SUSPENDED

    with _RANDOM_MODE_LOCK:
        was_running = _RANDOM_MODE_RUNNING
        _RANDOM_MODE_RUNNING = False
        _RANDOM_MODE_SUSPENDED = False
        return was_running, _RANDOM_CURRENT_GIF


def _suspend_random_mode() -> bool:
    """Pause the random gif loop while a temporary gif borrows the screen.

    Returns True when a running mode was suspended; the loop stays alive but
    does not cycle until _resume_random_mode is called.
    """
    global _RANDOM_MODE_SUSPENDED

    with _RANDOM_MODE_LOCK:
        if not _RANDOM_MODE_RUNNING:
            return False
        _RANDOM_MODE_SUSPENDED = True
        return True


def _resume_random_mode() -> None:
    """Lift a suspension made by _suspend_random_mode."""
    global _RANDOM_MODE_SUSPENDED

    with _RANDOM_MODE_LOCK:
        _RANDOM_MODE_SUSPENDED = False


def _is_image_mode_running() -> bool:
    with _RANDOM_IMAGE_MODE_LOCK:
        return _RANDOM_IMAGE_MODE_RUNNING


def _is_image_mode_suspended() -> bool:
    with _RANDOM_IMAGE_MODE_LOCK:
        return _RANDOM_IMAGE_MODE_SUSPENDED


def _stop_image_mode() -> tuple[bool, str | None]:
    """Stop the random image mode entirely. Returns (was_running, current_image)."""
    global _RANDOM_IMAGE_MODE_RUNNING, _RANDOM_IMAGE_MODE_SUSPENDED

    with _RANDOM_IMAGE_MODE_LOCK:
        was_running = _RANDOM_IMAGE_MODE_RUNNING
        _RANDOM_IMAGE_MODE_RUNNING = False
        _RANDOM_IMAGE_MODE_SUSPENDED = False
        return was_running, _RANDOM_CURRENT_IMAGE


def _suspend_image_mode() -> bool:
    """Pause the random image loop while a temporary gif borrows the screen.

    Returns True when a running mode was suspended; the loop stays alive but
    does not cycle until _resume_image_mode is called.
    """
    global _RANDOM_IMAGE_MODE_SUSPENDED

    with _RANDOM_IMAGE_MODE_LOCK:
        if not _RANDOM_IMAGE_MODE_RUNNING:
            return False
        _RANDOM_IMAGE_MODE_SUSPENDED = True
        return True


def _resume_image_mode() -> None:
    """Lift a suspension made by _suspend_image_mode."""
    global _RANDOM_IMAGE_MODE_SUSPENDED

    with _RANDOM_IMAGE_MODE_LOCK:
        _RANDOM_IMAGE_MODE_SUSPENDED = False


def _is_special_mode_running() -> bool:
    with _SPECIAL_MODE_LOCK:
        return _SPECIAL_MODE_RUNNING


def _is_special_mode_suspended() -> bool:
    with _SPECIAL_MODE_LOCK:
        return _SPECIAL_MODE_SUSPENDED


def _stop_special_mode() -> tuple[bool, str | None]:
    """Stop the special routine mode entirely. Returns (was_running, current_gif)."""
    global _SPECIAL_MODE_RUNNING, _SPECIAL_MODE_SUSPENDED
    with _SPECIAL_MODE_LOCK:
        was_running = _SPECIAL_MODE_RUNNING
        _SPECIAL_MODE_RUNNING = False
        _SPECIAL_MODE_SUSPENDED = False
        return was_running, _SPECIAL_CURRENT_GIF


def _suspend_special_mode() -> bool:
    """Pause the special routine loop while a temporary gif borrows the screen."""
    global _SPECIAL_MODE_SUSPENDED
    with _SPECIAL_MODE_LOCK:
        if not _SPECIAL_MODE_RUNNING:
            return False
        _SPECIAL_MODE_SUSPENDED = True
        return True


def _resume_special_mode() -> None:
    """Lift a suspension made by _suspend_special_mode."""
    global _SPECIAL_MODE_SUSPENDED
    with _SPECIAL_MODE_LOCK:
        _SPECIAL_MODE_SUSPENDED = False


def _is_cube_display_on() -> bool:
    """Return True when the Cube display is on (brightness above zero).

    An unreachable device counts as off, so the random gif loop pauses
    instead of hammering a dead endpoint with uploads.
    """
    try:
        return http._fetch_cube_brightness() > config.BRIGHTNESS_MIN
    except Exception:
        return False


def _wait_between_cycles(
    total_seconds: int, is_running, is_suspended, display_poll_seconds: int = 1
) -> None:
    """Count total_seconds down in 1s steps, pausing whenever needed.

    The countdown only advances while the mode keeps running, it is not
    suspended and the Cube display is on; otherwise the wait keeps polling
    every second without counting down, resuming the cycle afterwards.
    The display state (an HTTP query) is only re-checked every
    `display_poll_seconds`: chatty modes can space it out so constant HTTP
    traffic doesn't starve the Cube's GIF renderer. Stop/suspend still react
    within 1s regardless of this interval.
    """
    display_poll_seconds = max(1, display_poll_seconds)
    remaining = total_seconds
    since_poll = display_poll_seconds
    display_on = True
    while remaining > 0 and is_running():
        time.sleep(1)
        if not is_running():
            break
        if is_suspended():
            continue
        since_poll += 1
        if since_poll >= display_poll_seconds:
            since_poll = 0
            display_on = _is_cube_display_on()
        if display_on:
            remaining -= 1


def _sleep_interruptible(total_seconds: int) -> None:
    """Sleep for total_seconds in 1s steps so stop_random_gifs reacts fast.

    The countdown only advances while the Cube display is on and the mode is
    not suspended: when the display is off (or unreachable) or a temporary
    gif is being shown, the wait keeps polling every second without counting
    down, resuming the cycle afterwards.
    """
    _wait_between_cycles(total_seconds, _is_random_mode_running, _is_random_mode_suspended)


def _sleep_interruptible_for_images(total_seconds: int) -> None:
    """Sleep for total_seconds in 1s steps so stop_random_images reacts fast."""
    _wait_between_cycles(total_seconds, _is_image_mode_running, _is_image_mode_suspended)


def _sleep_interruptible_for_special(total_seconds: int, display_poll_seconds: int = 1) -> None:
    """Sleep interruptibly for the special routine (respects suspend/display off).

    The display state is re-checked every `display_poll_seconds` (default every
    second); the oiia flow passes a wider interval because constant HTTP
    polling starves GIF playback on the Cube.
    """
    _wait_between_cycles(
        total_seconds,
        _is_special_mode_running,
        _is_special_mode_suspended,
        display_poll_seconds,
    )
