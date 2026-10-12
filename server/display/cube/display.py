from __future__ import annotations

from ... import mcp
from . import config
from . import http
from . import state


@mcp.tool()
def set_cube_brightness(level: int = config.BRIGHTNESS_DEFAULT) -> dict[str, str]:
    """
    Sets the brightness of the Cube display.

    The level is clamped to the valid range [0, 100] before being sent to the
    Cube via its /set?brt= endpoint.

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

    if not response:
        return {"status": "success", "message": f"Cube brightness set to: {clamped}"}

    return {
        "status": "success",
        "message": f"Cube brightness set to: {clamped}. Device response: {response}",
    }


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

    The brightness level active before turning off is remembered in memory so it
    can be restored later with turn_cube_display_on. The level is queried from
    the device; if unavailable, the last remembered value or the default (50)
    is used instead.
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

    Uses the brightness saved before the display was turned off; if nothing is
    remembered (or the remembered value is 0), defaults to 50. The level is
    clamped to the valid range [0, 100].
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    if state._REMEMBERED_BRIGHTNESS is not None and state._REMEMBERED_BRIGHTNESS > config.BRIGHTNESS_MIN:
        level = state._REMEMBERED_BRIGHTNESS
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
