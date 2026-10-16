from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

# Absolute paths based on workspace structure
ENV_PATH: Final[Path] = Path(__file__).resolve().parents[3] / ".env"

load_dotenv(ENV_PATH)

CUBE_BASE_URL: Final[str] = os.environ.get("CUBE_BASE_URL", "").rstrip("/")

BRIGHTNESS_DEFAULT: Final[int] = 50
BRIGHTNESS_MIN: Final[int] = 0
BRIGHTNESS_MAX: Final[int] = 100

# Firmware time-based brightness schedule (/set?t1=&t2=&b1=&b2=&en=):
# t1/t2 bound the "HH:MM" day window, b1/b2 are the day/night brightness
# levels, en enables the schedule. The firmware UI fixes b1 at 50.
BRIGHTNESS_SCHEDULE_DEFAULT_START: Final[str] = "08:00"
BRIGHTNESS_SCHEDULE_DEFAULT_END: Final[str] = "22:00"
BRIGHTNESS_SCHEDULE_DEFAULT_DAY: Final[int] = 50
# Night brightness is always 0 (display off); intentionally not a parameter.

# SQLite file holding persistent cube state (last schedule, remembered
# brightness) that must survive server restarts. Lives under media/
# (gitignored) next to the galleries.
STATE_DB_FILE: Final[Path] = Path(__file__).resolve().parents[3] / "media" / "state.db"

CUBE_IMAGE_DIR: Final[str] = "/image"
ALLOWED_UPLOAD_SUFFIXES: Final[frozenset[str]] = frozenset({".gif", ".jpg", ".jpeg"})
IMAGE_REQUIRED_DIMENSIONS: Final[tuple[int, int]] = (240, 240)

# Upload tuning: the device writes uploads to flash and can momentarily stop
# answering while doing so, so posts wait generously for the response (with a
# short connect phase) and are retried once on transport-level failures such
# as read timeouts or dropped connections.
UPLOAD_CONNECT_TIMEOUT_SECONDS: Final[int] = 10
UPLOAD_TIMEOUT_SECONDS: Final[int] = 120
UPLOAD_ATTEMPTS: Final[int] = 2

# Minimum number of bytes that must remain free on the Cube after an upload;
# uploads that would leave less than this reserve are rejected.
UPLOAD_FREE_SPACE_BUFFER: Final[int] = 50 * 1024

JPEG_SAVE_QUALITY: Final[int] = 90

# Maximum length of the .jpg name stored in media/images by save_image_in_gallery.
IMAGE_NAME_MAX_LENGTH: Final[int] = 25

# Trailing suffixes stripped from the save name sent to save_image_in_gallery, which
# usually arrives without any suffix; anything else is kept as part of the name.
STRIPPABLE_IMAGE_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
)

TEMP_GIF_NAME: Final[str] = "tmp"
TEMP_GIF_DEFAULT_SECONDS: Final[int] = 5
TEMP_GIF_MIN_SECONDS: Final[int] = 1
TEMP_GIF_MAX_SECONDS: Final[int] = 30

# Seconds to wait after the audio ends before restoring the previous gif in
# show_temporary_gif_with_audio (also the grace applied when an explicit
# duration is shorter than the audio).
TEMP_RESTORE_AFTER_AUDIO_DELAY_SECONDS: Final[int] = 1
# Seconds to wait between the accepted /set request and the audio start in
# show_temporary_gif_with_audio. The Cube answers "OK" on receipt but still
# needs a moment to load the file and start rendering; without this pause the
# audio runs ahead of the first visible frame.
TEMP_AUDIO_START_DELAY_SECONDS: Final[int] = 4
# Upper bound (seconds) waiting for the audio to finish before restoring
# anyway in show_temporary_gif_with_audio, so a stuck player cannot suspend
# the random/special modes forever.
TEMP_AUDIO_END_WAIT_MAX_SECONDS: Final[int] = 300

# Local folder holding the gif pool used by the random gif mode.
RANDOM_GIF_DIR: Final[Path] = Path(__file__).resolve().parents[3] / "media" / "gifs"

# Name under which every picked gif is temporarily uploaded to the Cube, so a
# new random gif simply overwrites the previous one.
RANDOM_GIF_NAME: Final[str] = "random.gif"

RANDOM_GIF_DEFAULT_SECONDS: Final[int] = 300
RANDOM_GIF_MIN_SECONDS: Final[int] = 5
RANDOM_GIF_MAX_SECONDS: Final[int] = 3600

# Local folder holding the image pool used by the random image mode.
RANDOM_IMAGE_DIR: Final[Path] = Path(__file__).resolve().parents[3] / "media" / "images"

# Suffixes accepted in the random image pool. Every picked image is uploaded
# to the Cube under RANDOM_IMAGE_NAME, so only jpg/jpeg sources make sense.
LOCAL_IMAGE_SUFFIXES: Final[frozenset[str]] = frozenset({".jpg", ".jpeg"})

# Name under which every picked image is temporarily uploaded to the Cube, so a
# new random image simply overwrites the previous one.
RANDOM_IMAGE_NAME: Final[str] = "random.jpg"

RANDOM_IMAGE_DEFAULT_SECONDS: Final[int] = 300
RANDOM_IMAGE_MIN_SECONDS: Final[int] = 5
RANDOM_IMAGE_MAX_SECONDS: Final[int] = 3600

# Special routine (e.g. pato-gira) mode state. Alternates between the two
# gifs of a routine stored under media/special/gifs/<routine> (e.g. pato-gira
# contains pato-gira.gif and pato-gira-rev.gif). The cube memory is cleared
# first, both gifs are uploaded, then displayed in a continuous 60s (1 min) loop
# simple sin calculos extra.
SPECIAL_GIF_ROOT: Final[Path] = Path(__file__).resolve().parents[3] / "media" / "special" / "gifs"
SPECIAL_DEFAULT_SECONDS: Final[int] = 60
SPECIAL_MIN_SECONDS: Final[int] = 1
SPECIAL_MAX_SECONDS: Final[int] = 3600

# Oiia timer defaults. Oiia runs on the unified special state (see state.py):
# _SPECIAL_GIFS holds the preloaded random batch, _SPECIAL_INTERVAL is `every`.
OIIA_DEFAULT_EVERY: Final[int] = 60
OIIA_MIN_EVERY: Final[int] = 10
OIIA_MAX_EVERY: Final[int] = 3600
OIIA_DEFAULT_DURATION: Final[int] = 10
OIIA_MIN_DURATION: Final[int] = 3
OIIA_MAX_DURATION: Final[int] = 600
OIIA_DEFAULT_RENEW: Final[int] = 600
OIIA_MIN_RENEW: Final[int] = 0
OIIA_MAX_RENEW: Final[int] = 86400
# Seconds between Cube display-state checks while the oiia loop counts down.
# The firmware starves GIF playback under constant HTTP chatter, so the loop
# stays mostly silent (stop/suspend still react within 1s).
OIIA_DISPLAY_POLL_SECONDS: Final[int] = 15
