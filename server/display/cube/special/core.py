from __future__ import annotations

from .... import mcp
from .. import config
from .. import state
from . import oiia
from . import pato_gira


@mcp.resource("cube://special")
def get_special_status() -> str:
    """
    Returns the state of the special routine mode (e.g. pato-gira, oiia).

    Reports whether the routine is running (or paused because display is off
    or suspended while a temporary gif is shown) and which gif is currently
    displayed. Generic routines show the full alternating list; oiia shows its
    default gif, the preloaded random batch and the every/duration/renew
    timers.
    """
    with state._SPECIAL_MODE_LOCK:
        running = state._SPECIAL_MODE_RUNNING
        suspended = state._SPECIAL_MODE_SUSPENDED
        current = state._SPECIAL_CURRENT_GIF
        routine = state._SPECIAL_CURRENT_ROUTINE
        gifs = list(state._SPECIAL_GIFS) if state._SPECIAL_GIFS else None
        interval = state._SPECIAL_INTERVAL
        oiia_duration = state._SPECIAL_OIIA_DURATION
        oiia_renew = state._SPECIAL_OIIA_RENEW

    if not running:
        status_text = "stopped"
    elif suspended:
        status_text = "running (suspended: temporary gif being shown)"
    elif state._is_cube_display_on():
        status_text = "running"
    else:
        status_text = "running (paused: Cube display is off)"

    lines = [f"Special routine: {status_text}"]
    if routine:
        lines.append(f"Routine: {routine}")
    if routine == "oiia":
        lines.extend(oiia._oiia_status_lines(gifs, interval, oiia_duration, oiia_renew))
    elif gifs:
        lines.extend(pato_gira._pato_gira_status_lines(gifs, interval))
    if current:
        lines.append(f"Current gif: {current}")
    else:
        lines.append("No special gif has been shown yet.")
    if not routine and not running:
        available = ", ".join(pato_gira._list_special_routines()) or "none"
        lines.append(f"Available routines: {available}")

    return "\n".join(lines)


@mcp.tool()
def start_special_routine(
    routine: str,
    seconds: int = config.SPECIAL_DEFAULT_SECONDS,
    every: int = config.OIIA_DEFAULT_EVERY,
    duration: int = config.OIIA_DEFAULT_DURATION,
    renew: int = config.OIIA_DEFAULT_RENEW,
) -> dict[str, str]:
    """
    Starts a special routine (pato-gira, oiia, ...) on the Cube display.

    For generic routines (e.g. pato-gira) it clears all files from the Cube's
    memory, uploads the two gifs from media/special/gifs/<routine> (e.g.
    pato-gira.gif and pato-gira-rev.gif) and continuously alternates between
    them every `seconds` (default 60 / 1 min) via a simple background
    timer/process. Original gifs are uploaded as-is sin restricciones. The
    first gif is shown before this call returns; a background thread then
    switches to the opposite gif every interval forever until
    stop_special_routine is called.

    The `oiia` routine keeps media/special/gifs/oiia/oiia.gif on screen and
    shows randomly picked gifs from media/special/gifs/oiia/random every
    `every` seconds for `duration` seconds each (repeats allowed), renewing
    the preloaded batch every `renew` seconds. `seconds` is ignored for
    `oiia`.

    Args:
        routine: Name of the routine directory under media/special/gifs
            (required, e.g. "pato-gira" or "oiia").
        seconds: Seconds each gif stays on screen before switching
            (default 60, clamped to [1, 3600]). Ignored for `oiia`.
        every: Only for `oiia`: seconds between random gif appearances
            (default 60, clamped to [10, 3600]).
        duration: Only for `oiia`: seconds each random gif stays on screen
            (default 10, clamped to [3, 600]). Must be less than `every`.
        renew: Only for `oiia`: seconds between preloaded batch renewals
            (default 600 = 10 min, clamped to [0, 86400]). 0 disables
            auto-renew.
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    routine = routine.strip().strip("/").strip()
    if not routine:
        return {"status": "error", "message": "Routine name is required."}

    if routine == "oiia":
        return oiia._start_special_oiia(every=every, duration=duration, renew=renew)
    return pato_gira._start_special_pato_gira(routine, seconds)


@mcp.tool()
def stop_special_routine() -> dict[str, str]:
    """
    Stops the special routine started by start_special_routine
    (generic ones and oiia share this unified mode).

    The loop stops; whatever was last displayed remains on the Cube.
    """
    was_running, current = state._stop_special_mode()
    if not was_running:
        return {"status": "success", "message": "Special routine is not running."}
    msg = "Special routine stopped."
    if current:
        msg += f" {current} remains displayed."
    return {"status": "success", "message": msg}
