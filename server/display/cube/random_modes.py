from __future__ import annotations

import base64
import threading
import time

from ... import mcp
from . import config
from . import files
from . import gallery
from . import http
from . import images
from . import state


def _run_random_cycle(exclude: str | None = None) -> tuple[bool, str]:
    """Upload and display one random local gif as random.gif on the Cube.

    Returns (True, gif_name) on success or (False, error_message) on failure.
    """
    try:
        gif_path = gallery._pick_random_gif(exclude)
        if gif_path is None:
            return False, f"No .gif files found in {config.RANDOM_GIF_DIR}."

        encoded = base64.b64encode(gif_path.read_bytes()).decode("ascii")
        result = files.upload_cube_image(encoded, config.RANDOM_GIF_NAME)
        if result["status"] != "success":
            return False, result["message"]

        response = http._set_cube_gif(config.RANDOM_GIF_NAME)
        if "FAIL" in response.upper():
            return False, f"Cube refused to display {config.RANDOM_GIF_NAME}. Response: {response}"

        return True, gif_path.name
    except Exception as exc:
        return False, str(exc)


def _run_random_image_cycle(exclude: str | None = None) -> tuple[bool, str]:
    """Upload and display one random local image as random.jpg on the Cube.

    Returns (True, image_name) on success or (False, error_message) on failure.
    """
    try:
        image_path = gallery._pick_random_image(exclude)
        if image_path is None:
            return False, f"No .jpg files found in {config.RANDOM_IMAGE_DIR}."

        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        result = files.upload_cube_image(encoded, config.RANDOM_IMAGE_NAME)
        if result["status"] != "success":
            return False, result["message"]

        response = http._set_cube_gif(config.RANDOM_IMAGE_NAME)
        if "FAIL" in response.upper():
            return False, f"Cube refused to display {config.RANDOM_IMAGE_NAME}. Response: {response}"

        return True, image_path.name
    except Exception as exc:
        return False, str(exc)


def _random_gif_loop(seconds: int, first_gif: str) -> None:
    """Keep uploading a new random gif every `seconds` until the mode stops.

    Runs in a background thread after start_random_gifs displayed the first
    gif. While the Cube display is off the loop stays paused, and any failed
    cycle is simply retried after the next wait.
    """
    previous = first_gif
    try:
        while state._is_random_mode_running():
            state._sleep_interruptible(seconds)
            if not state._is_random_mode_running():
                break

            ok, value = _run_random_cycle(previous)
            if ok:
                with state._RANDOM_MODE_LOCK:
                    state._RANDOM_CURRENT_GIF = value
                previous = value
    finally:
        with state._RANDOM_MODE_LOCK:
            state._RANDOM_MODE_RUNNING = False


def _random_image_loop(seconds: int, first_image: str) -> None:
    """Keep uploading a new random image every `seconds` until the mode stops.

    Runs in a background thread after start_random_images displayed the first
    image. While the Cube display is off the loop stays paused, and any failed
    cycle is simply retried after the next wait.
    """
    previous = first_image
    try:
        while state._is_image_mode_running():
            state._sleep_interruptible_for_images(seconds)
            if not state._is_image_mode_running():
                break

            ok, value = _run_random_image_cycle(previous)
            if ok:
                with state._RANDOM_IMAGE_MODE_LOCK:
                    state._RANDOM_CURRENT_IMAGE = value
                previous = value
    finally:
        with state._RANDOM_IMAGE_MODE_LOCK:
            state._RANDOM_IMAGE_MODE_RUNNING = False


@mcp.resource("cube://random-gif")
def get_random_gif_status() -> str:
    """
    Returns the state of the random gif mode.

    Reports whether the mode is running (or paused because the Cube display
    is off, or suspended while a temporary gif is shown) and which temporary
    gif (random.gif) is currently being used.
    """
    with state._RANDOM_MODE_LOCK:
        running = state._RANDOM_MODE_RUNNING
        suspended = state._RANDOM_MODE_SUSPENDED
        current = state._RANDOM_CURRENT_GIF

    if not running:
        state_text = "stopped"
    elif suspended:
        state_text = "running (suspended: temporary gif being shown)"
    elif state._is_cube_display_on():
        state_text = "running"
    else:
        state_text = "running (paused: Cube display is off)"

    lines = [f"Random gif mode: {state_text}"]
    if current:
        lines.append(f"Current temporary gif: {current} (uploaded as {config.RANDOM_GIF_NAME})")
    else:
        lines.append("No temporary gif has been shown yet.")

    return "\n".join(lines)


@mcp.resource("cube://random-image")
def get_random_image_status() -> str:
    """
    Returns the state of the random image mode.

    Reports whether the mode is running (or paused because the Cube display
    is off, or suspended while a temporary gif is shown) and which temporary
    image (random.jpg) is currently being used.
    """
    with state._RANDOM_IMAGE_MODE_LOCK:
        running = state._RANDOM_IMAGE_MODE_RUNNING
        suspended = state._RANDOM_IMAGE_MODE_SUSPENDED
        current = state._RANDOM_CURRENT_IMAGE

    if not running:
        state_text = "stopped"
    elif suspended:
        state_text = "running (suspended: temporary gif being shown)"
    elif state._is_cube_display_on():
        state_text = "running"
    else:
        state_text = "running (paused: Cube display is off)"

    lines = [f"Random image mode: {state_text}"]
    if current:
        lines.append(f"Current temporary image: {current} (uploaded as {config.RANDOM_IMAGE_NAME})")
    else:
        lines.append("No temporary image has been shown yet.")

    return "\n".join(lines)


@mcp.tool()
def start_random_gifs(seconds: int = config.RANDOM_GIF_DEFAULT_SECONDS) -> dict[str, str]:
    """
    Starts cycling random gifs from media/gifs on the Cube display.

    Picks a random gif from the local gifs folder, uploads it to the Cube as
    random.gif (overwriting the previous one) and displays it. Every `seconds`
    another random gif replaces it, forever, until stop_random_gifs is called;
    consecutive repeats are avoided when possible. The first gif is shown
    before this call returns. Read the cube://random-gif resource to know
    which gif is currently being used. If the random image mode is running it
    is stopped first, so both random modes never fight over the screen.

    Args:
        seconds: Seconds each gif stays on screen before switching to the next
            random gif (default 300 = 5 minutes, clamped to [5, 3600]).
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    with state._RANDOM_MODE_LOCK:
        busy = state._RANDOM_MODE_RUNNING
    if busy:
        return {
            "status": "error",
            "message": "Random gif mode is already running. Call stop_random_gifs first.",
        }

    clamped = max(config.RANDOM_GIF_MIN_SECONDS, min(config.RANDOM_GIF_MAX_SECONDS, seconds))

    if not gallery._list_local_gifs():
        return {"status": "error", "message": f"No .gif files found in {config.RANDOM_GIF_DIR}."}

    with state._RANDOM_MODE_LOCK:
        if state._RANDOM_MODE_RUNNING:
            return {
                "status": "error",
                "message": "Random gif mode is already running. Call stop_random_gifs first.",
            }
        state._RANDOM_MODE_RUNNING = True
        state._RANDOM_MODE_SUSPENDED = False

    image_was_running, _previous_image = state._stop_image_mode()
    special_was_running, _previous_special = state._stop_special_mode()

    current = state._RANDOM_CURRENT_GIF
    ok, value = _run_random_cycle(current)

    if not ok:
        with state._RANDOM_MODE_LOCK:
            state._RANDOM_MODE_RUNNING = False
        return {"status": "error", "message": f"Failed to display the first random gif: {value}"}

    with state._RANDOM_MODE_LOCK:
        state._RANDOM_CURRENT_GIF = value

    threading.Thread(target=_random_gif_loop, args=(clamped, value), daemon=True).start()

    message = (
        f"Random gif mode started: {value} is displayed as {config.RANDOM_GIF_NAME}; "
        f"a new random gif will be shown every {clamped} seconds."
    )
    if image_was_running:
        message += " Random image mode stopped."
    if special_was_running:
        message += " Special routine stopped."

    return {"status": "success", "message": message}


@mcp.tool()
def stop_random_gifs() -> dict[str, str]:
    """
    Stops the random gif cycling started by start_random_gifs.

    The loop stops picking new gifs; whatever was uploaded as random.gif
    remains displayed on the Cube.
    """
    was_running, current = state._stop_random_mode()

    if not was_running:
        return {"status": "success", "message": "Random gif mode is not running."}

    message = "Random gif mode stopped."
    if current:
        message += f" {current} ({config.RANDOM_GIF_NAME}) remains displayed."

    return {"status": "success", "message": message}


@mcp.tool()
def start_random_images(seconds: int = config.RANDOM_IMAGE_DEFAULT_SECONDS) -> dict[str, str]:
    """
    Starts cycling random images from media/images on the Cube display.

    Picks a random image from the local images folder, uploads it to the Cube
    as random.jpg (overwriting the previous one) and displays it. Every
    `seconds` another random image replaces it, forever, until
    stop_random_images is called; consecutive repeats are avoided when
    possible. Images must be exactly 240x240. The first image is shown before
    this call returns. Read the cube://random-image resource to know which
    image is currently being used. If the random gif mode is running it is
    stopped first, so both random modes never fight over the screen.

    Args:
        seconds: Seconds each image stays on screen before switching to the
            next random image (default 300 = 5 minutes, clamped to [5, 3600]).
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    with state._RANDOM_IMAGE_MODE_LOCK:
        busy = state._RANDOM_IMAGE_MODE_RUNNING
    if busy:
        return {
            "status": "error",
            "message": "Random image mode is already running. Call stop_random_images first.",
        }

    clamped = max(config.RANDOM_IMAGE_MIN_SECONDS, min(config.RANDOM_IMAGE_MAX_SECONDS, seconds))

    if not gallery._list_local_images():
        return {"status": "error", "message": f"No .jpg files found in {config.RANDOM_IMAGE_DIR}."}

    with state._RANDOM_IMAGE_MODE_LOCK:
        if state._RANDOM_IMAGE_MODE_RUNNING:
            return {
                "status": "error",
                "message": "Random image mode is already running. Call stop_random_images first.",
            }
        state._RANDOM_IMAGE_MODE_RUNNING = True
        state._RANDOM_IMAGE_MODE_SUSPENDED = False

    gif_was_running, _previous_gif = state._stop_random_mode()
    special_was_running, _previous_special = state._stop_special_mode()

    current = state._RANDOM_CURRENT_IMAGE
    ok, value = _run_random_image_cycle(current)

    if not ok:
        with state._RANDOM_IMAGE_MODE_LOCK:
            state._RANDOM_IMAGE_MODE_RUNNING = False
        return {"status": "error", "message": f"Failed to display the first random image: {value}"}

    with state._RANDOM_IMAGE_MODE_LOCK:
        state._RANDOM_CURRENT_IMAGE = value

    threading.Thread(target=_random_image_loop, args=(clamped, value), daemon=True).start()

    message = (
        f"Random image mode started: {value} is displayed as {config.RANDOM_IMAGE_NAME}; "
        f"a new random image will be shown every {clamped} seconds."
    )
    if gif_was_running:
        message += " Random gif mode stopped."
    if special_was_running:
        message += " Special routine stopped."

    return {"status": "success", "message": message}


@mcp.tool()
def stop_random_images() -> dict[str, str]:
    """
    Stops the random image cycling started by start_random_images.

    The loop stops picking new images; whatever was uploaded as random.jpg
    remains displayed on the Cube.
    """
    was_running, current = state._stop_image_mode()

    if not was_running:
        return {"status": "success", "message": "Random image mode is not running."}

    message = "Random image mode stopped."
    if current:
        message += f" {current} ({config.RANDOM_IMAGE_NAME}) remains displayed."

    return {"status": "success", "message": message}
