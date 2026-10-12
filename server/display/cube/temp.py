from __future__ import annotations

import base64
import threading
import time
from pathlib import Path

from ...audio.play import _build_player_command
from ...audio.play import _decode_audio_payload
from ...audio.play import _is_ffplay_running
from ...audio.play import _play_audio_bytes_async
from ...audio.play import _probe_audio_duration
from ...audio.play import stop_audio
from ... import mcp
from . import config
from . import files
from . import http
from . import images
from . import state


def _restore_previous_gif(
    previous: str,
    seconds: int,
    resume_random: bool = False,
    resume_image: bool = False,
    resume_special: bool = False,
) -> None:
    """Sleep for `seconds` and then restore the previous gif on the Cube.

    Runs in a background thread after show_temporary_gif has already replied,
    so any error here cannot be reported back to the client. When
    `resume_random`/`resume_image`/`resume_special` is True the suspended
    random gif/image/special mode is resumed after the restore.
    """
    try:
        time.sleep(seconds)
        if previous:
            http._set_cube_gif(previous)
    except Exception:
        pass
    finally:
        with state._TEMP_GIF_LOCK:
            state._TEMP_GIF_RUNNING = False
        if resume_random:
            state._resume_random_mode()
        if resume_image:
            state._resume_image_mode()
        if resume_special:
            state._resume_special_mode()


@mcp.tool()
def show_temporary_gif(data: str, filename: str, seconds: int = config.TEMP_GIF_DEFAULT_SECONDS) -> dict[str, str]:
    """
    Shows a gif or jpg/jpeg image temporarily on the Cube display.

    The flow is: read the gif currently displayed (to restore it later), upload
    the new image as tmp.gif/tmp.jpg with the same validations as
    upload_cube_image (Base64 decode, allowed extension, 240x240 dimensions,
    free space, upload confirmation) and display it. Other formats (png, webp,
    bmp...) are not rejected: they are converted to an exact 240x240 JPEG and
    shown as tmp.jpg. The call returns
    immediately; after the configured seconds a background job restores the
    previous gif. Only one temporary gif can run at a time: while one is being
    shown, new requests are rejected until it finishes. If the random gif mode
    is running it is suspended while the temporary gif is on screen and
    resumed automatically after the previous gif is restored. The same applies
    to the random image mode.

    Args:
        data: Image bytes encoded in Base64 (client-side).
        filename: Name of the image, used to determine its type (.gif -> tmp.gif,
            anything else -> tmp.jpg).
        seconds: Seconds to show the image (default 5, clamped to [1, 30]).
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    with state._TEMP_GIF_LOCK:
        busy = state._TEMP_GIF_RUNNING
    if busy:
        return {
            "status": "error",
            "message": "A temporary gif is already being shown. Wait for it to finish before starting another.",
        }

    clamped = max(config.TEMP_GIF_MIN_SECONDS, min(config.TEMP_GIF_MAX_SECONDS, seconds))

    name = Path(filename.strip()).name

    try:
        payload = images._decode_image(data)
    except Exception as e:
        return {"status": "error", "message": f"Failed to decode image {name}: {e}"}

    if not payload:
        return {"status": "error", "message": f"Image is empty: {name}."}

    name, payload, conversion_error = images._to_cube_compatible_image(name, payload)
    if conversion_error:
        return {"status": "error", "message": conversion_error}

    tmp_name = f"{config.TEMP_GIF_NAME}.gif" if name.lower().endswith(".gif") else f"{config.TEMP_GIF_NAME}.jpg"

    was_running_random = state._suspend_random_mode()
    was_running_image = state._suspend_image_mode()
    was_running_special = state._suspend_special_mode()

    try:
        current = http._fetch_cube_current_gif()
    except Exception as e:
        if was_running_random:
            state._resume_random_mode()
        if was_running_image:
            state._resume_image_mode()
        if was_running_special:
            state._resume_special_mode()
        return {"status": "error", "message": f"Failed to read current gif from Cube: {e}"}

    result = files.upload_cube_image(base64.b64encode(payload).decode("ascii"), tmp_name)
    if result["status"] != "success":
        if was_running_random:
            state._resume_random_mode()
        if was_running_image:
            state._resume_image_mode()
        if was_running_special:
            state._resume_special_mode()
        return result

    with state._TEMP_GIF_LOCK:
        if state._TEMP_GIF_RUNNING:
            if was_running_random:
                state._resume_random_mode()
            if was_running_image:
                state._resume_image_mode()
            if was_running_special:
                state._resume_special_mode()
            return {
                "status": "error",
                "message": "A temporary gif is already being shown. Wait for it to finish before starting another.",
            }
        state._TEMP_GIF_RUNNING = True

    try:
        response = http._set_cube_gif(tmp_name)
    except Exception as e:
        with state._TEMP_GIF_LOCK:
            state._TEMP_GIF_RUNNING = False
        if was_running_random:
            state._resume_random_mode()
        if was_running_image:
            state._resume_image_mode()
        if was_running_special:
            state._resume_special_mode()
        return {"status": "error", "message": f"Failed to display temporary gif {tmp_name}: {e}"}

    if "FAIL" in response.upper():
        with state._TEMP_GIF_LOCK:
            state._TEMP_GIF_RUNNING = False
        if was_running_random:
            state._resume_random_mode()
        if was_running_image:
            state._resume_image_mode()
        if was_running_special:
            state._resume_special_mode()
        return {
            "status": "error",
            "message": f"Cube refused to display temporary gif {tmp_name}. Response: {response}",
        }

    previous = current.removeprefix(f"{config.CUBE_IMAGE_DIR}/").lstrip("/")
    threading.Thread(
        target=_restore_previous_gif,
        args=(previous, clamped, was_running_random, was_running_image, was_running_special),
        daemon=True,
    ).start()

    paused_note = ""
    if was_running_random:
        paused_note = " Random gif mode paused (it will resume automatically)."
    elif was_running_image:
        paused_note = " Random image mode paused (it will resume automatically)."
    elif was_running_special:
        paused_note = " Special routine paused (it will resume automatically)."

    if not previous:
        return {
            "status": "success",
            "message": (
                f"Temporary gif {tmp_name} is now displayed for {clamped} seconds. "
                f"No previous gif to restore.{paused_note}"
            ),
        }

    return {
        "status": "success",
        "message": (
            f"Temporary gif {tmp_name} is now displayed for {clamped} seconds. "
            f"{previous} will be restored automatically.{paused_note}"
        ),
    }


def _restore_temp_gif_with_audio(
    previous: str,
    display_start: float,
    seconds: int | None,
    resume_random: bool = False,
    resume_image: bool = False,
    resume_special: bool = False,
) -> None:
    """Restore the previous gif after the longer of `seconds` vs audio end.

    Runs in a background thread after show_temporary_gif_with_audio has
    already replied, so any error here cannot be reported back to the client.
    Waits for the audio to finish (bounded by TEMP_AUDIO_END_WAIT_MAX_SECONDS
    so a stuck player cannot suspend the display modes forever), then restores
    the previous gif at the later of `display_start + seconds` (when an
    explicit duration was given) or TEMP_RESTORE_AFTER_AUDIO_DELAY_SECONDS
    after the audio finished — so the image always lasts at least as long as
    the audio. Resumes whichever display mode was suspended.
    """
    try:
        waited = 0
        while waited < config.TEMP_AUDIO_END_WAIT_MAX_SECONDS and _is_ffplay_running():
            time.sleep(1)
            waited += 1
        audio_end = time.monotonic()
        grace_target = audio_end + config.TEMP_RESTORE_AFTER_AUDIO_DELAY_SECONDS
        if seconds is not None:
            target = max(display_start + seconds, grace_target)
        else:
            target = grace_target
        remaining = target - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
        if previous:
            http._set_cube_gif(previous)
    except Exception:
        pass
    finally:
        with state._TEMP_GIF_LOCK:
            state._TEMP_GIF_RUNNING = False
        if resume_random:
            state._resume_random_mode()
        if resume_image:
            state._resume_image_mode()
        if resume_special:
            state._resume_special_mode()


@mcp.tool()
def show_temporary_gif_with_audio(
    data: str,
    filename: str,
    audio_data: str,
    audio_name: str = "",
    seconds: int | None = None,
) -> dict[str, str]:
    """
    Shows a gif or jpg/jpeg image temporarily on the Cube display and plays
    an audio alongside it.

    Works like show_temporary_gif (same image validations, same upload as
    tmp.gif/tmp.jpg, same suspension of any running random/special mode, same
    background restore of the previous gif), plus audio: any audio already
    playing is stopped first, then the new audio starts only after the
    temporary image has been verified on the Cube and displayed, plus a short
    delay (TEMP_AUDIO_START_DELAY_SECONDS) so the Cube finishes switching
    frames before the sound starts. The call returns immediately; playback
    continues in the background.

    Args:
        data: Image bytes encoded in Base64 (client-side).
        filename: Name of the image, used to determine its type (.gif -> tmp.gif,
            anything else -> tmp.jpg).
        audio_data: Audio bytes encoded in Base64 (client-side, 10 MB max).
            Required.
        audio_name: Original audio filename, only used for status messages.
        seconds: Seconds to show the image (clamped to [1, 30]). When omitted,
            the previous gif is restored TEMP_RESTORE_AFTER_AUDIO_DELAY_SECONDS
            (1 s) after the audio finishes. When given but shorter than the
            audio, it is ignored (reported back) and the image lasts until 1 s
            after the audio finishes.
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    with state._TEMP_GIF_LOCK:
        busy = state._TEMP_GIF_RUNNING
    if busy:
        return {
            "status": "error",
            "message": "A temporary gif is already being shown. Wait for it to finish before starting another.",
        }

    clamped = (
        max(config.TEMP_GIF_MIN_SECONDS, min(config.TEMP_GIF_MAX_SECONDS, seconds))
        if seconds is not None
        else None
    )

    name = Path(filename.strip()).name

    try:
        payload = images._decode_image(data)
    except Exception as e:
        return {"status": "error", "message": f"Failed to decode image {name}: {e}"}

    if not payload:
        return {"status": "error", "message": f"Image is empty: {name}."}

    name, payload, conversion_error = images._to_cube_compatible_image(name, payload)
    if conversion_error:
        return {"status": "error", "message": conversion_error}

    tmp_name = f"{config.TEMP_GIF_NAME}.gif" if name.lower().endswith(".gif") else f"{config.TEMP_GIF_NAME}.jpg"

    if not audio_data.strip():
        return {"status": "error", "message": "Audio data is required."}
    try:
        audio_bytes = _decode_audio_payload(audio_data)
    except ValueError as e:
        return {"status": "error", "message": f"Failed to decode audio: {e}"}
    if not audio_bytes:
        return {"status": "error", "message": "Audio data is empty."}
    try:
        _build_player_command()
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}
    audio_duration = _probe_audio_duration(audio_bytes)

    was_running_random = state._suspend_random_mode()
    was_running_image = state._suspend_image_mode()
    was_running_special = state._suspend_special_mode()

    def _resume_all() -> None:
        if was_running_random:
            state._resume_random_mode()
        if was_running_image:
            state._resume_image_mode()
        if was_running_special:
            state._resume_special_mode()

    try:
        current = http._fetch_cube_current_gif()
    except Exception as e:
        _resume_all()
        return {"status": "error", "message": f"Failed to read current gif from Cube: {e}"}

    result = files.upload_cube_image(base64.b64encode(payload).decode("ascii"), tmp_name)
    if result["status"] != "success":
        _resume_all()
        return result

    with state._TEMP_GIF_LOCK:
        if state._TEMP_GIF_RUNNING:
            _resume_all()
            return {
                "status": "error",
                "message": "A temporary gif is already being shown. Wait for it to finish before starting another.",
            }
        state._TEMP_GIF_RUNNING = True

    try:
        response = http._set_cube_gif(tmp_name)
    except Exception as e:
        with state._TEMP_GIF_LOCK:
            state._TEMP_GIF_RUNNING = False
        _resume_all()
        return {"status": "error", "message": f"Failed to display temporary gif {tmp_name}: {e}"}

    if "FAIL" in response.upper():
        with state._TEMP_GIF_LOCK:
            state._TEMP_GIF_RUNNING = False
        _resume_all()
        return {
            "status": "error",
            "message": f"Cube refused to display temporary gif {tmp_name}. Response: {response}",
        }

    # The image is verified on the Cube and the /set request accepted — but
    # that only acknowledges receipt, so stop any current audio, give the Cube
    # a moment to actually switch frames, and only then start the new audio.
    had_previous_audio = _is_ffplay_running()
    stop_audio()
    time.sleep(config.TEMP_AUDIO_START_DELAY_SECONDS)
    try:
        _play_audio_bytes_async(audio_bytes)
        audio_label = (
            f"{audio_name.strip() or 'audio'} ({len(audio_bytes)} bytes)"
        )
    except Exception as e:
        with state._TEMP_GIF_LOCK:
            state._TEMP_GIF_RUNNING = False
        _resume_all()
        return {
            "status": "error",
            "message": f"Temporary gif {tmp_name} is displayed but the audio failed: {e}",
        }

    previous = current.removeprefix(f"{config.CUBE_IMAGE_DIR}/").lstrip("/")
    display_start = time.monotonic()
    threading.Thread(
        target=_restore_temp_gif_with_audio,
        args=(previous, display_start, clamped, was_running_random, was_running_image, was_running_special),
        daemon=True,
    ).start()

    grace_unit = (
        "second" if config.TEMP_RESTORE_AFTER_AUDIO_DELAY_SECONDS == 1 else "seconds"
    )
    if clamped is None:
        restore_note = (
            f"{previous} will be restored {config.TEMP_RESTORE_AFTER_AUDIO_DELAY_SECONDS} {grace_unit} "
            f"after the audio finishes."
        )
    else:
        restore_note = f"{previous} will be restored automatically after {clamped} seconds."

    paused_note = ""
    if was_running_random:
        paused_note = " Random gif mode paused (it will resume automatically)."
    elif was_running_image:
        paused_note = " Random image mode paused (it will resume automatically)."
    elif was_running_special:
        paused_note = " Special routine paused (it will resume automatically)."

    parts = [f"Temporary gif {tmp_name} is now displayed with {audio_label}."]
    if had_previous_audio:
        parts.append("Previous audio stopped.")
    if (
        clamped is not None
        and audio_duration is not None
        and clamped < audio_duration
    ):
        parts.append(
            f"Requested {clamped}s is shorter than the audio (~{audio_duration:.0f}s) "
            f"and will be ignored; the image stays until "
            f"{config.TEMP_RESTORE_AFTER_AUDIO_DELAY_SECONDS} {grace_unit} after the audio finishes."
        )
    if not previous:
        parts.append("No previous gif to restore.")
    else:
        parts.append(restore_note)
    if paused_note:
        parts.append(paused_note.strip())

    return {"status": "success", "message": " ".join(parts)}
