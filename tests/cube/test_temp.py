import base64
import unittest
from io import BytesIO
from unittest.mock import Mock, patch

from PIL import Image

from server.display import cube as cube_module
from server.display.cube import (
    show_temporary_gif,
    show_temporary_gif_with_audio,
    _restore_previous_gif,
    _restore_temp_gif_with_audio,
)


def _image_bytes(fmt: str, width: int, height: int) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format=fmt)
    return buffer.getvalue()


class ShowTemporaryGifTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_running = cube_module.state._TEMP_GIF_RUNNING
        cube_module.state._TEMP_GIF_RUNNING = False

    def tearDown(self) -> None:
        cube_module.state._TEMP_GIF_RUNNING = self._original_running

    def _encoded(self, data: bytes) -> str:
        return base64.b64encode(data).decode()

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_shows_tmp_and_schedules_background_restore(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("tmp.gif is now displayed for 5 seconds", result["message"])
        self.assertIn("test.gif will be restored automatically", result["message"])
        mock_current.assert_called_once()
        mock_upload.assert_called_once_with(self._encoded(b"gifdata"), "tmp.gif")
        mock_set.assert_called_once_with("tmp.gif")
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("test.gif", 5, False, False, False),
            daemon=True,
        )
        mock_thread_cls.return_value.start.assert_called_once()
        self.assertTrue(cube_module.state._TEMP_GIF_RUNNING)

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/photo.jpg")
    def test_maps_jpeg_extension_to_tmp_jpg(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"jpgdata"), "photo.JPEG")

        self.assertEqual(result["status"], "success")
        mock_upload.assert_called_once_with(self._encoded(b"jpgdata"), "tmp.jpg")
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("photo.jpg", 5, False, False, False),
            daemon=True,
        )

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_clamps_seconds_above_max(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif", seconds=100)

        self.assertEqual(result["status"], "success")
        self.assertIn("displayed for 30 seconds", result["message"])
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("test.gif", 30, False, False, False),
            daemon=True,
        )

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_clamps_seconds_below_min(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif", seconds=0)

        self.assertEqual(result["status"], "success")
        self.assertIn("displayed for 1 seconds", result["message"])
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("test.gif", 1, False, False, False),
            daemon=True,
        )

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="")
    def test_reports_no_previous_gif_to_restore(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("No previous gif to restore", result["message"])
        mock_set.assert_called_once_with("tmp.gif")
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("", 5, False, False, False),
            daemon=True,
        )

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.files.upload_cube_image")
    @patch("server.display.cube.http._fetch_cube_current_gif")
    def test_rejects_when_a_temporary_gif_is_already_running(
        self, mock_current: Mock, mock_upload: Mock, mock_thread_cls: Mock
    ) -> None:
        cube_module.state._TEMP_GIF_RUNNING = True

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("A temporary gif is already being shown", result["message"])
        mock_current.assert_not_called()
        mock_upload.assert_not_called()
        mock_thread_cls.assert_not_called()

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_converts_png_to_tmp_jpg_before_uploading(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(_image_bytes("PNG", 500, 300)), "picture.png")

        self.assertEqual(result["status"], "success")
        encoded, name = mock_upload.call_args[0]
        self.assertEqual(name, "tmp.jpg")
        with Image.open(BytesIO(base64.b64decode(encoded))) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(img.size, (240, 240))

    @patch("server.display.cube.files.upload_cube_image")
    def test_returns_error_when_conversion_fails(self, mock_upload: Mock) -> None:
        result = show_temporary_gif(self._encoded(b"data"), "picture.webp")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to convert image picture.webp to JPEG", result["message"])
        mock_upload.assert_not_called()

    def test_returns_error_when_nameless_format_cannot_be_converted(self) -> None:
        with patch("server.display.cube.files.upload_cube_image") as mock_upload:
            result = show_temporary_gif(self._encoded(b"data"), "noext")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to convert image noext to JPEG", result["message"])
        mock_upload.assert_not_called()

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.config.CUBE_BASE_URL", ""):
            result = show_temporary_gif(self._encoded(b"data"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.files.upload_cube_image")
    @patch("server.display.cube.http._fetch_cube_current_gif", side_effect=RuntimeError("timeout"))
    def test_returns_error_when_current_gif_cannot_be_read(
        self, mock_current: Mock, mock_upload: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to read current gif from Cube", result["message"])
        mock_upload.assert_not_called()
        mock_thread_cls.assert_not_called()

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch(
        "server.display.cube.files.upload_cube_image",
        return_value={"status": "error", "message": "Image must be 240x240 (got 100x100): tmp.gif."},
    )
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_propagates_upload_error_without_displaying(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image must be 240x240", result["message"])
        mock_set.assert_not_called()
        mock_thread_cls.assert_not_called()
        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", side_effect=RuntimeError("connection refused"))
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_returns_error_when_display_fails_and_releases_flag(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to display temporary gif tmp.gif", result["message"])
        mock_thread_cls.assert_not_called()
        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="FAIL")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_returns_error_when_display_refused_and_releases_flag(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Cube refused to display temporary gif", result["message"])
        mock_thread_cls.assert_not_called()
        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)


class ShowTemporaryGifWithAudioTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_running = cube_module.state._TEMP_GIF_RUNNING
        cube_module.state._TEMP_GIF_RUNNING = False

    def tearDown(self) -> None:
        cube_module.state._TEMP_GIF_RUNNING = self._original_running

    def _encoded(self, data: bytes) -> str:
        return base64.b64encode(data).decode()

    @patch("server.display.cube.temp._probe_audio_duration", return_value=None)
    @patch("server.display.cube.state.time.sleep")
    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    @patch("server.display.cube.temp._play_audio_bytes_async")
    @patch("server.display.cube.temp.stop_audio", return_value={"status": "stopped", "message": "idle"})
    @patch("server.display.cube.temp._is_ffplay_running", return_value=False)
    def test_shows_tmp_and_plays_audio(
        self, mock_running: Mock, mock_stop: Mock, mock_play: Mock,
        mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock,
        mock_sleep: Mock, mock_probe: Mock,
    ) -> None:
        result = show_temporary_gif_with_audio(self._encoded(b"gifdata"), "tmp.gif", self._encoded(b"audiodata"), seconds=5)

        self.assertEqual(result["status"], "success")
        self.assertIn("tmp.gif is now displayed", result["message"])
        self.assertIn("test.gif will be restored automatically after 5 seconds", result["message"])
        mock_stop.assert_called_once()
        mock_sleep.assert_called_once_with(4)
        mock_play.assert_called_once()
        played = mock_play.call_args[0][0]
        self.assertEqual(played, b"audiodata")
        from unittest.mock import ANY
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_temp_gif_with_audio,
            args=("test.gif", ANY, 5, False, False, False),
            daemon=True,
        )
        self.assertTrue(cube_module.state._TEMP_GIF_RUNNING)

    @patch("server.display.cube.temp._probe_audio_duration", return_value=None)
    @patch("server.display.cube.state.time.sleep")
    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    @patch("server.display.cube.temp._play_audio_bytes_async")
    @patch("server.display.cube.temp.stop_audio", return_value={"status": "stopped", "message": "idle"})
    @patch("server.display.cube.temp._is_ffplay_running", return_value=True)
    def test_stops_previous_audio_first(
        self, mock_running: Mock, mock_stop: Mock, mock_play: Mock,
        mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock,
        mock_sleep: Mock, mock_probe: Mock,
    ) -> None:
        result = show_temporary_gif_with_audio(self._encoded(b"gifdata"), "tmp.gif", self._encoded(b"audiodata"), seconds=5)

        self.assertEqual(result["status"], "success")
        self.assertIn("Previous audio stopped.", result["message"])
        mock_stop.assert_called_once()
        mock_play.assert_called_once()

    @patch("server.display.cube.temp._probe_audio_duration", return_value=None)
    @patch("server.display.cube.state.time.sleep")
    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    @patch("server.display.cube.temp._play_audio_bytes_async")
    @patch("server.display.cube.temp.stop_audio", return_value={"status": "stopped", "message": "idle"})
    @patch("server.display.cube.temp._is_ffplay_running", return_value=False)
    def test_defaults_to_restore_after_audio(
        self, mock_running: Mock, mock_stop: Mock, mock_play: Mock,
        mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock,
        mock_sleep: Mock, mock_probe: Mock,
    ) -> None:
        result = show_temporary_gif_with_audio(self._encoded(b"gifdata"), "tmp.gif", self._encoded(b"audiodata"))

        self.assertEqual(result["status"], "success")
        self.assertIn("1 second after the audio finishes", result["message"])
        from unittest.mock import ANY
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_temp_gif_with_audio,
            args=("test.gif", ANY, None, False, False, False),
            daemon=True,
        )

    @patch("server.display.cube.state.time.sleep")
    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    @patch("server.display.cube.temp._play_audio_bytes_async")
    @patch("server.display.cube.temp.stop_audio", return_value={"status": "stopped", "message": "idle"})
    @patch("server.display.cube.temp._is_ffplay_running", return_value=False)
    @patch("server.display.cube.temp._probe_audio_duration", return_value=30.0)
    def test_short_seconds_ignored_with_notice(
        self, mock_probe: Mock, mock_running: Mock, mock_stop: Mock, mock_play: Mock,
        mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock,
        mock_sleep: Mock,
    ) -> None:
        result = show_temporary_gif_with_audio(self._encoded(b"gifdata"), "tmp.gif", self._encoded(b"audiodata"), seconds=5)

        self.assertEqual(result["status"], "success")
        self.assertIn("shorter than the audio (~30s)", result["message"])
        self.assertIn("will be ignored", result["message"])
        from unittest.mock import ANY
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_temp_gif_with_audio,
            args=("test.gif", ANY, 5, False, False, False),
            daemon=True,
        )
        self.assertTrue(cube_module.state._TEMP_GIF_RUNNING)

    @patch("server.display.cube.state.time.sleep")
    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    @patch("server.display.cube.temp._play_audio_bytes_async")
    @patch("server.display.cube.temp.stop_audio", return_value={"status": "stopped", "message": "idle"})
    @patch("server.display.cube.temp._is_ffplay_running", return_value=False)
    @patch("server.display.cube.temp._probe_audio_duration", return_value=3.0)
    def test_long_seconds_kept_without_notice(
        self, mock_probe: Mock, mock_running: Mock, mock_stop: Mock, mock_play: Mock,
        mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock,
        mock_sleep: Mock,
    ) -> None:
        result = show_temporary_gif_with_audio(self._encoded(b"gifdata"), "tmp.gif", self._encoded(b"audiodata"), seconds=10)

        self.assertEqual(result["status"], "success")
        self.assertIn("restored automatically after 10 seconds", result["message"])
        self.assertNotIn("ignored", result["message"])

    def test_rejects_when_audio_missing(self) -> None:
        result = show_temporary_gif_with_audio(self._encoded(b"gifdata"), "tmp.gif", "")
        self.assertEqual(result["status"], "error")
        self.assertIn("Audio data is required", result["message"])

    def test_rejects_invalid_audio_base64(self) -> None:
        result = show_temporary_gif_with_audio(self._encoded(b"gifdata"), "tmp.gif", "!!!not-base64!!!")
        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to decode audio", result["message"])

    def test_rejects_when_busy(self) -> None:
        cube_module.state._TEMP_GIF_RUNNING = True
        result = show_temporary_gif_with_audio(self._encoded(b"gifdata"), "tmp.gif", self._encoded(b"audiodata"))
        self.assertEqual(result["status"], "error")
        self.assertIn("already being shown", result["message"])


class RestoreTempGifWithAudioTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_running = cube_module.state._TEMP_GIF_RUNNING
        cube_module.state._TEMP_GIF_RUNNING = True

    def tearDown(self) -> None:
        cube_module.state._TEMP_GIF_RUNNING = self._original_running

    @patch("server.display.cube.state._resume_special_mode")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.state.time.sleep")
    @patch("server.display.cube.temp._is_ffplay_running", side_effect=[True, False])
    def test_restores_after_audio_end(
        self, mock_running: Mock, mock_sleep: Mock, mock_set: Mock, mock_resume: Mock
    ) -> None:
        import time
        from server.display.cube import _restore_temp_gif_with_audio
        _restore_temp_gif_with_audio("old.gif", time.monotonic(), None, resume_special=True)
        mock_set.assert_called_once_with("old.gif")
        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)
        mock_resume.assert_called_once()

    @patch("server.display.cube.state._resume_special_mode")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.state.time.sleep")
    @patch("server.display.cube.temp._is_ffplay_running", return_value=True)
    def test_gives_up_after_max_wait(
        self, mock_running: Mock, mock_sleep: Mock, mock_set: Mock, mock_resume: Mock
    ) -> None:
        import time
        from server.display.cube import _restore_temp_gif_with_audio
        _restore_temp_gif_with_audio("old.gif", time.monotonic(), None, resume_special=True)
        mock_set.assert_called_once_with("old.gif")
        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)

    @patch("server.display.cube.state._resume_special_mode")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.state.time.sleep")
    @patch("server.display.cube.temp._is_ffplay_running", side_effect=[True, False])
    def test_long_seconds_win_over_audio_end(
        self, mock_running: Mock, mock_sleep: Mock, mock_set: Mock, mock_resume: Mock
    ) -> None:
        import time
        from server.display.cube import _restore_temp_gif_with_audio
        _restore_temp_gif_with_audio("old.gif", time.monotonic(), 30, resume_special=True)
        mock_set.assert_called_once_with("old.gif")
        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)


class RestorePreviousGifTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_running = cube_module.state._TEMP_GIF_RUNNING
        cube_module.state._TEMP_GIF_RUNNING = False

    def tearDown(self) -> None:
        cube_module.state._TEMP_GIF_RUNNING = self._original_running

    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.state.time.sleep")
    def test_sleeps_then_restores_previous_gif(self, mock_sleep: Mock, mock_set: Mock) -> None:
        cube_module.state._TEMP_GIF_RUNNING = True

        _restore_previous_gif("test.gif", 7)

        mock_sleep.assert_called_once_with(7)
        mock_set.assert_called_once_with("test.gif")
        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)

    @patch("server.display.cube.http._set_cube_gif")
    @patch("server.display.cube.state.time.sleep")
    def test_skips_restore_when_no_previous_gif(self, mock_sleep: Mock, mock_set: Mock) -> None:
        cube_module.state._TEMP_GIF_RUNNING = True

        _restore_previous_gif("", 3)

        mock_sleep.assert_called_once_with(3)
        mock_set.assert_not_called()
        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)

    @patch(
        "server.display.cube.http._set_cube_gif",
        side_effect=RuntimeError("connection refused"),
    )
    @patch("server.display.cube.state.time.sleep")
    def test_swallows_restore_errors_and_releases_flag(
        self, mock_sleep: Mock, mock_set: Mock
    ) -> None:
        cube_module.state._TEMP_GIF_RUNNING = True

        _restore_previous_gif("test.gif", 2)

        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)


class RandomModeInteractionFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._originals = (
            cube_module.state._RANDOM_MODE_RUNNING,
            cube_module.state._RANDOM_CURRENT_GIF,
            cube_module.state._RANDOM_IMAGE_MODE_RUNNING,
            cube_module.state._RANDOM_IMAGE_MODE_SUSPENDED,
            cube_module.state._RANDOM_CURRENT_IMAGE,
            cube_module.state._TEMP_GIF_RUNNING,
        )
        cube_module.state._RANDOM_MODE_RUNNING = False
        cube_module.state._RANDOM_CURRENT_GIF = None
        cube_module.state._RANDOM_IMAGE_MODE_RUNNING = False
        cube_module.state._RANDOM_IMAGE_MODE_SUSPENDED = False
        cube_module.state._RANDOM_CURRENT_IMAGE = None
        cube_module.state._TEMP_GIF_RUNNING = False

    def tearDown(self) -> None:
        (
            cube_module.state._RANDOM_MODE_RUNNING,
            cube_module.state._RANDOM_CURRENT_GIF,
            cube_module.state._RANDOM_IMAGE_MODE_RUNNING,
            cube_module.state._RANDOM_IMAGE_MODE_SUSPENDED,
            cube_module.state._RANDOM_CURRENT_IMAGE,
            cube_module.state._TEMP_GIF_RUNNING,
        ) = self._originals


class ShowTemporaryGifSuspendsRandomModeTests(RandomModeInteractionFixture):
    def _encoded(self, data: bytes) -> str:
        return base64.b64encode(data).decode()

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/random.gif")
    def test_suspends_running_random_mode_before_showing_tmp(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        cube_module.state._RANDOM_MODE_RUNNING = True
        cube_module.state._RANDOM_CURRENT_GIF = "gifx.gif"

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Random gif mode paused (it will resume automatically).", result["message"])
        self.assertTrue(cube_module.state._RANDOM_MODE_RUNNING)
        self.assertTrue(cube_module.state._RANDOM_MODE_SUSPENDED)
        # The previous gif read after suspending is the random.gif upload and
        # the restore job will resume the random mode afterwards.
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("random.gif", 5, True, False, False),
            daemon=True,
        )

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/test.gif")
    def test_no_paused_note_when_random_not_running(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertNotIn("Random gif mode paused", result["message"])
        self.assertFalse(cube_module.state._RANDOM_MODE_SUSPENDED)

    @patch("server.display.cube.files.upload_cube_image")
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/random.gif")
    def test_resumes_random_mode_when_upload_fails(
        self, mock_current: Mock, mock_upload: Mock
    ) -> None:
        cube_module.state._RANDOM_MODE_RUNNING = True
        cube_module.state._suspend_random_mode()
        mock_upload.return_value = {"status": "error", "message": "boom"}

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertTrue(cube_module.state._RANDOM_MODE_RUNNING)
        self.assertFalse(cube_module.state._RANDOM_MODE_SUSPENDED)

    @patch(
        "server.display.cube.http._fetch_cube_current_gif",
        side_effect=RuntimeError("timeout"),
    )
    def test_resumes_random_mode_when_current_gif_read_fails(self, mock_current: Mock) -> None:
        cube_module.state._RANDOM_MODE_RUNNING = True
        cube_module.state._suspend_random_mode()

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertFalse(cube_module.state._RANDOM_MODE_SUSPENDED)

    @patch("server.display.cube.state.threading.Thread")
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.files.upload_cube_image", return_value={"status": "success", "message": "uploaded"})
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/random.jpg")
    def test_suspends_running_image_mode_before_showing_tmp(
        self, mock_current: Mock, mock_upload: Mock, mock_set: Mock, mock_thread_cls: Mock
    ) -> None:
        cube_module.state._RANDOM_IMAGE_MODE_RUNNING = True
        cube_module.state._RANDOM_CURRENT_IMAGE = "imagex.jpg"

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Random image mode paused (it will resume automatically).", result["message"])
        self.assertNotIn("Random gif mode paused", result["message"])
        self.assertTrue(cube_module.state._RANDOM_IMAGE_MODE_RUNNING)
        self.assertTrue(cube_module.state._RANDOM_IMAGE_MODE_SUSPENDED)
        # The previous gif read after suspending is the random.jpg upload and
        # the restore job will resume the random image mode afterwards.
        mock_thread_cls.assert_called_once_with(
            target=cube_module._restore_previous_gif,
            args=("random.jpg", 5, False, True, False),
            daemon=True,
        )

    @patch("server.display.cube.files.upload_cube_image")
    @patch("server.display.cube.http._fetch_cube_current_gif", return_value="/image/random.jpg")
    def test_resumes_image_mode_when_upload_fails(
        self, mock_current: Mock, mock_upload: Mock
    ) -> None:
        cube_module.state._RANDOM_IMAGE_MODE_RUNNING = True
        cube_module.state._suspend_image_mode()
        mock_upload.return_value = {"status": "error", "message": "boom"}

        result = show_temporary_gif(self._encoded(b"gifdata"), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertTrue(cube_module.state._RANDOM_IMAGE_MODE_RUNNING)
        self.assertFalse(cube_module.state._RANDOM_IMAGE_MODE_SUSPENDED)


class RestorePreviousGifResumesRandomTests(RandomModeInteractionFixture):
    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.state.time.sleep")
    def test_resume_random_true_clears_suspension_after_restore(
        self, mock_sleep: Mock, mock_set: Mock
    ) -> None:
        cube_module.state._TEMP_GIF_RUNNING = True
        cube_module.state._RANDOM_MODE_RUNNING = True
        cube_module.state._suspend_random_mode()

        cube_module._restore_previous_gif("random.gif", 3, resume_random=True)

        mock_sleep.assert_called_once_with(3)
        mock_set.assert_called_once_with("random.gif")
        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)
        self.assertFalse(cube_module.state._RANDOM_MODE_SUSPENDED)
        self.assertTrue(cube_module.state._RANDOM_MODE_RUNNING)

    @patch("server.display.cube.http._set_cube_gif")
    @patch("server.display.cube.state.time.sleep")
    def test_resume_random_false_leaves_state_alone(
        self, mock_sleep: Mock, mock_set: Mock
    ) -> None:
        cube_module.state._TEMP_GIF_RUNNING = True

        cube_module._restore_previous_gif("test.gif", 2)

        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)
        self.assertFalse(cube_module.state._RANDOM_MODE_SUSPENDED)
        self.assertFalse(cube_module.state._RANDOM_MODE_RUNNING)

    @patch("server.display.cube.http._set_cube_gif", return_value="OK")
    @patch("server.display.cube.state.time.sleep")
    def test_resume_image_true_clears_image_suspension_after_restore(
        self, mock_sleep: Mock, mock_set: Mock
    ) -> None:
        cube_module.state._TEMP_GIF_RUNNING = True
        cube_module.state._RANDOM_IMAGE_MODE_RUNNING = True
        cube_module.state._suspend_image_mode()

        cube_module._restore_previous_gif("random.jpg", 3, resume_image=True)

        mock_sleep.assert_called_once_with(3)
        mock_set.assert_called_once_with("random.jpg")
        self.assertFalse(cube_module.state._TEMP_GIF_RUNNING)
        self.assertFalse(cube_module.state._RANDOM_IMAGE_MODE_SUSPENDED)
        self.assertTrue(cube_module.state._RANDOM_IMAGE_MODE_RUNNING)


if __name__ == "__main__":
    unittest.main()
