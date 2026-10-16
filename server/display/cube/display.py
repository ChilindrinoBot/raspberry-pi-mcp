from __future__ import annotations

import re

from ... import mcp
from . import config
from . import http
from . import state
from . import store

_SCHEDULE_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _remembered_hours() -> dict[str, object] | None:
    """Return the remembered schedule hours (memory first, store fallback)."""
    remembered = state._BRIGHTNESS_SCHEDULE
    if remembered is None:
        stored = store.get_cube_config().get("schedule")
        remembered = stored if isinstance(stored, dict) else None
    return remembered if isinstance(remembered, dict) else None


def _resolve_day_level() -> tuple[int, str]:
    """Resolve the day level: live brightness, else 50.

    The Cube reports its last manual level (scheduled dimming does not touch
    the register), so the live read is the preference; an off or unreachable
    display falls back to the default.
    """
    try:
        live = http._fetch_cube_brightness()
    except Exception:
        live = config.BRIGHTNESS_MIN
    if live > config.BRIGHTNESS_MIN:
        return live, " (current brightness)"
    return config.BRIGHTNESS_SCHEDULE_DEFAULT_DAY, ""


def _refresh_schedule_day(level: int) -> str:
    """Re-send the remembered enabled schedule with a new day level.

    Hours are never touched. Returns a message note, or "" when no enabled
    schedule is remembered. Failures are reported, never raised, so the
    manual set that triggered the refresh keeps its success.
    """
    remembered = _remembered_hours()
    if remembered is None or not remembered.get("enabled"):
        return ""
    try:
        response = http._set_cube_brightness_schedule(
            str(remembered["time2"]), str(remembered["time1"]), level, 0, True
        )
    except Exception as e:
        return f"Schedule refresh failed: {e}."
    if "FAIL" in response.upper():
        return f"Schedule refresh failed: {response}."
    return f"Schedule day updated to {level}."



@mcp.tool()
def set_cube_brightness(level: int = config.BRIGHTNESS_DEFAULT) -> dict[str, str]:
    """
    Sets the brightness of the Cube display.

    The level is clamped to the valid range [0, 100] before being sent to the
    Cube via its /set?brt= endpoint. A positive level also refreshes a
    remembered enabled schedule with the new day level (same hours); 0 never
    touches the schedule.

    Args:
        level: Brightness level between 0 and 100 (default: 50).
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    clamped = max(config.BRIGHTNESS_MIN, min(config.BRIGHTNESS_MAX, level))

    try:
        response = http._set_cube_brightness(clamped)
    except Exception as e:
        return {"status": "error", "message": f"Failed to set brightness on Cube: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to set brightness {clamped}. Response: {response}",
        }

    note = ""
    if clamped > config.BRIGHTNESS_MIN:
        note = _refresh_schedule_day(clamped)

    # Both branches are success: HTTP 200 without "FAIL" already is. The body
    # is not a success signal (usually "OK", once observed empty), so the raw
    # reply is kept for debugging only.
    if not response:
        message = f"Cube brightness set to: {clamped}"
    else:
        message = f"Cube brightness set to: {clamped}. Device response: {response}"
    if note:
        message += f" {note}"

    return {"status": "success", "message": message}


@mcp.resource("cube://brightness")
def get_cube_brightness() -> str:
    """
    Returns the current brightness level of the Cube display.
    """
    if not config.CUBE_BASE_URL:
        return "CUBE_BASE_URL is not configured. Set it in the .env file."

    try:
        brightness = http._fetch_cube_brightness()
    except Exception as e:
        return f"Failed to fetch brightness from Cube: {e}"

    return f"Current Cube brightness: {brightness}"


BRIGHTNESS_NIGHT = 0 # Alwyas off

@mcp.tool()
def set_cube_brightness_schedule(
    time1: str = config.BRIGHTNESS_SCHEDULE_DEFAULT_START,
    time2: str = config.BRIGHTNESS_SCHEDULE_DEFAULT_END,
    enabled: bool = True,
) -> dict[str, str]:
    """
    Sets the Cube firmware time-based brightness schedule.

    Outside the time1-time2 day window the display turns off (night is
    always 0, not configurable); inside the window it uses the live
    brightness (50 when the display is off or unreachable). The schedule
    is delegated to the firmware via its
    /set?t1=&t2=&b1=&b2=&en= endpoint with the night window (t1=time2,
    t2=time1, like the firmware Night Mode GUI), which enforces the levels
    internally. The sent hours are remembered server-side because the
    firmware does not expose them for reading back.

    Args:
        time1: Day window start as "HH:MM" (default: 08:00).
        time2: Day window end as "HH:MM" (default: 22:00).
        enabled: Switch the schedule on (True) or off (False, default True).
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    time1 = time1.strip()
    time2 = time2.strip()
    if not _SCHEDULE_TIME_RE.match(time1) or not _SCHEDULE_TIME_RE.match(time2):
        return {
            "status": "error",
            "message": f"Invalid schedule window: {time1!r}-{time2!r}. Use HH:MM (00:00-23:59).",
        }
    if time1 == time2:
        return {
            "status": "error",
            "message": f"Invalid schedule window: {time1!r}-{time2!r}. Start and end must differ.",
        }

    day, day_source = _resolve_day_level()

    try:
        response = http._set_cube_brightness_schedule(time2, time1, day, BRIGHTNESS_NIGHT, enabled)
    except Exception as e:
        return {"status": "error", "message": f"Failed to set brightness schedule on Cube: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to set brightness schedule. Response: {response}",
        }

    state._BRIGHTNESS_SCHEDULE = {"time1": time1, "time2": time2, "enabled": enabled}
    store.update_cube_config(schedule=state._BRIGHTNESS_SCHEDULE)

    state_word = "enabled" if enabled else "disabled"
    message = (
        f"Cube brightness schedule {state_word}: "
        f"day {time1}-{time2} at {day}{day_source}, night at {BRIGHTNESS_NIGHT}."
    )
    if response:
        message += f" Device response: {response}"

    return {"status": "success", "message": message}


@mcp.resource("cube://brightness-schedule")
def get_cube_brightness_schedule() -> str:
    """
    Returns the last time-based brightness schedule sent to the Cube.

    The firmware enforces the schedule internally and does not expose it
    for reading back, so this reports what this server last configured
    (falling back to the persisted hours after a restart, or that nothing
    was sent yet). The day level shown is live-read from the Cube.
    """
    remembered = _remembered_hours()
    if remembered is None:
        return "No brightness schedule has been configured yet."

    try:
        day = http._fetch_cube_brightness()
    except Exception:
        day = None
    day_text = str(day) if day is not None else "unknown"
    state_word = "enabled" if remembered["enabled"] else "disabled"
    return (
        f"Cube brightness schedule ({state_word}): "
        f"day {remembered['time1']}-{remembered['time2']} at {day_text}, "
        f"night at 0 (enforced by the Cube firmware)."
    )


@mcp.resource("cube://current-gif")
def get_cube_current_gif() -> str:
    """
    Returns the gif currently set on the Cube display.
    """
    if not config.CUBE_BASE_URL:
        return "CUBE_BASE_URL is not configured. Set it in the .env file."

    try:
        gif = http._fetch_cube_current_gif()
    except Exception as e:
        return f"Failed to fetch current gif from Cube: {e}"

    if not gif:
        return "No gif is currently set on the Cube."

    name = gif.removeprefix(f"{config.CUBE_IMAGE_DIR}/").lstrip("/")
    return f"Current Cube gif: {name}"


@mcp.tool()
def turn_cube_display_off() -> dict[str, str]:
    """
    Turns off the Cube display by setting its brightness to 0.

    The level active before turning off is remembered in session memory so
    it can be restored with turn_cube_display_on (nothing is persisted).
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    try:
        previous = http._fetch_cube_brightness()
    except Exception:
        previous = state._REMEMBERED_BRIGHTNESS if state._REMEMBERED_BRIGHTNESS is not None else config.BRIGHTNESS_DEFAULT

    if previous > config.BRIGHTNESS_MIN:
        state._REMEMBERED_BRIGHTNESS = max(config.BRIGHTNESS_MIN, min(config.BRIGHTNESS_MAX, previous))

    try:
        response = http._set_cube_brightness(config.BRIGHTNESS_MIN)
    except Exception as e:
        return {"status": "error", "message": f"Failed to turn off Cube display: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to turn off display. Response: {response}",
        }

    remembered = state._REMEMBERED_BRIGHTNESS if state._REMEMBERED_BRIGHTNESS is not None else config.BRIGHTNESS_DEFAULT
    message = f"Cube display turned off. Brightness will be restored to {remembered} on next power on."
    if response:
        message += f" Device response: {response}"

    return {"status": "success", "message": message}


@mcp.tool()
def turn_cube_display_on() -> dict[str, str]:
    """
    Turns on the Cube display by restoring the remembered brightness level.

    Uses the level saved before the display was turned off (session memory
    only); if nothing is remembered, defaults to 50. The level is clamped
    to the valid range [0, 100].
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    remembered = state._REMEMBERED_BRIGHTNESS
    if remembered is not None and remembered > config.BRIGHTNESS_MIN:
        level = remembered
    else:
        level = config.BRIGHTNESS_DEFAULT
    clamped = max(config.BRIGHTNESS_MIN, min(config.BRIGHTNESS_MAX, level))

    try:
        response = http._set_cube_brightness(clamped)
    except Exception as e:
        return {"status": "error", "message": f"Failed to turn on Cube display: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to turn on display. Response: {response}",
        }

    message = f"Cube display turned on at brightness {clamped}."
    if response:
        message += f" Device response: {response}"

    return {"status": "success", "message": message}


@mcp.tool()
def set_cube_gif(gif: str) -> dict[str, str]:
    """
    Displays a gif on the Cube display.

    Validates that the gif exists in the Cube's file list before sending the /set request.
    If the random gif or random image mode is running it is stopped first, so
    the requested gif stays on screen.

    Args:
        gif: Name (or relative path) of the gif to display on the Cube.
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    gif = gif.strip().lstrip("/")
    if not gif:
        return {"status": "error", "message": "Gif name is required."}

    try:
        available = http._fetch_cube_gifs()
    except Exception as e:
        return {"status": "error", "message": f"Failed to verify gif availability: {e}"}

    if gif not in available:
        return {
            "status": "error",
            "message": f"Gif not found on Cube: {gif}. Available: {', '.join(available) or 'none'}.",
        }

    was_running_gif, _previous_random = state._stop_random_mode()
    was_running_image, _previous_random_image = state._stop_image_mode()
    was_running_special, _previous_special = state._stop_special_mode()

    try:
        response = http._set_cube_gif(gif)
    except Exception as e:
        return {"status": "error", "message": f"Failed to set gif on Cube: {e}"}

    if "FAIL" in response.upper():
        return {
            "status": "error",
            "message": f"Cube refused to set gif {gif}. Response: {response}",
        }

    parts = [f"Cube gif set to: {gif}"]
    if was_running_gif:
        parts.append("Random gif mode stopped.")
    if was_running_image:
        parts.append("Random image mode stopped.")
    if was_running_special:
        parts.append("Special routine stopped.")
    if response:
        parts.append(f"Device response: {response}")

    return {"status": "success", "message": ". ".join(parts)}


def _restore_persistent_state() -> None:
    """Reload persisted cube state at boot and refresh the firmware schedule.

    Production entrypoint only (`server/main.py`, never tests): when the
    persisted schedule is enabled, re-sends it (day level live-read) so the
    firmware holds fresh parameters and the resource reports the schedule
    again. Failures are logged, never raised.
    """
    schedule = store.get_cube_config().get("schedule")
    if not isinstance(schedule, dict) or not schedule.get("enabled"):
        return
    try:
        result = set_cube_brightness_schedule(
            str(schedule["time1"]),
            str(schedule["time2"]),
            True,
        )
    except Exception as e:
        print(f"brightness schedule: boot refresh failed: {e}")
        return
    if result.get("status") != "success":
        print(f"brightness schedule: boot refresh failed: {result.get('message')}")
    else:
        print(
            f"brightness schedule: resumed {schedule.get('time1')}-{schedule.get('time2')}"
        )
