from __future__ import annotations

"""Special routines for the Cube display (one module per routine).

Each routine module owns its flow on the unified special state (see
server.display.cube.state): implement `_start_special_<mode>(...)` plus a
`<mode>_status_lines(...)` detail helper there, re-export both below, and add
a dispatch branch in core.start_special_routine (plus a status branch in
core.get_special_status). The pato-gira flow also serves any plain routine
directory until it gets its own module. Current routines: pato_gira (spinning
duck, alternating gifs), oiia (cat, default gif + random interruptions).
"""

from . import core
from . import oiia
from . import pato_gira

from .core import (
    get_special_status,
    start_special_routine,
    stop_special_routine,
)
from .pato_gira import (
    _list_special_gifs,
    _list_special_routines,
    _pato_gira_status_lines,
    _special_loop,
    _start_special_pato_gira,
)
from .oiia import (
    OIIA_DIR,
    OIIA_DEFAULT_GIF_NAME,
    OIIA_RANDOM_DIR,
    _oiia_status_lines,
    _list_oiia_random_gifs,
    _oiia_fill_randoms,
    _oiia_refresh_randoms,
    _oiia_loop,
    _start_special_oiia,
)

__all__ = [
    "core",
    "oiia",
    "pato_gira",
    "get_special_status",
    "start_special_routine",
    "stop_special_routine",
    "_list_special_gifs",
    "_list_special_routines",
    "_pato_gira_status_lines",
    "_special_loop",
    "_start_special_pato_gira",
    "OIIA_DIR",
    "OIIA_DEFAULT_GIF_NAME",
    "OIIA_RANDOM_DIR",
    "_oiia_status_lines",
    "_list_oiia_random_gifs",
    "_oiia_fill_randoms",
    "_oiia_refresh_randoms",
    "_oiia_loop",
    "_start_special_oiia",
]
