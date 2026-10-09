import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from server.display import cube as cube_module
from server.display.cube import (
    _list_special_gifs,
    _list_special_routines,
    _list_oiia_random_gifs,
    _oiia_fill_randoms,
    _oiia_loop,
    _oiia_refresh_randoms,
    _special_loop,
    _wait_between_cycles,
    get_special_status,
    start_special_routine,
    stop_special_routine,
    SPECIAL_GIF_ROOT,
    SPECIAL_DEFAULT_SECONDS,
    OIIA_DEFAULT_EVERY,
    OIIA_DEFAULT_DURATION,
    OIIA_DEFAULT_RENEW,
    OIIA_DEFAULT_GIF_NAME,
    OIIA_DISPLAY_POLL_SECONDS,
)


class SpecialModeStateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._orig = (
            cube_module._SPECIAL_MODE_RUNNING,
            cube_module._SPECIAL_MODE_SUSPENDED,
            cube_module._SPECIAL_CURRENT_GIF,
            cube_module._SPECIAL_CURRENT_ROUTINE,
            cube_module._SPECIAL_GIFS,
            cube_module._SPECIAL_INTERVAL,
            cube_module._SPECIAL_OIIA_DURATION,
            cube_module._SPECIAL_OIIA_RENEW,
        )
        cube_module._SPECIAL_MODE_RUNNING = False
        cube_module._SPECIAL_MODE_SUSPENDED = False
        cube_module._SPECIAL_CURRENT_GIF = None
        cube_module._SPECIAL_CURRENT_ROUTINE = None
        cube_module._SPECIAL_GIFS = None
        cube_module._SPECIAL_INTERVAL = None
        cube_module._SPECIAL_OIIA_DURATION = None
        cube_module._SPECIAL_OIIA_RENEW = None

    def tearDown(self) -> None:
        (
            cube_module._SPECIAL_MODE_RUNNING,
            cube_module._SPECIAL_MODE_SUSPENDED,
            cube_module._SPECIAL_CURRENT_GIF,
            cube_module._SPECIAL_CURRENT_ROUTINE,
            cube_module._SPECIAL_GIFS,
            cube_module._SPECIAL_INTERVAL,
            cube_module._SPECIAL_OIIA_DURATION,
            cube_module._SPECIAL_OIIA_RENEW,
        ) = self._orig


class ListSpecialGifsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = Path(__import__("tempfile").mkdtemp())
        (self._tmpdir / "pato-gira").mkdir(parents=True)
        (self._tmpdir / "pato-gira" / "pato-gira.gif").write_bytes(b"a")
        (self._tmpdir / "pato-gira" / "pato-gira-rev.gif").write_bytes(b"b")
        (self._tmpdir / "other").mkdir(parents=True)
        (self._tmpdir / "other" / "x.jpg").write_bytes(b"c")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_lists_gifs_sorted(self) -> None:
        with patch.object(cube_module, "SPECIAL_GIF_ROOT", self._tmpdir):
            gifs = _list_special_gifs("pato-gira")
        self.assertEqual([p.name for p in gifs], ["pato-gira-rev.gif", "pato-gira.gif"])

    def test_returns_empty_when_routine_missing(self) -> None:
        with patch.object(cube_module, "SPECIAL_GIF_ROOT", self._tmpdir):
            self.assertEqual(_list_special_gifs("missing"), [])

    def test_list_routines(self) -> None:
        with patch.object(cube_module, "SPECIAL_GIF_ROOT", self._tmpdir):
            routines = _list_special_routines()
        self.assertIn("pato-gira", routines)
        self.assertIn("other", routines)


class OiiaRoutineGifsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = Path(__import__("tempfile").mkdtemp())
        (self._tmpdir / "oiia").mkdir(parents=True)
        (self._tmpdir / "oiia" / "oiia.gif").write_bytes(b"oiia-data")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_oiia_listed_as_routine(self) -> None:
        with patch.object(cube_module, "SPECIAL_GIF_ROOT", self._tmpdir):
            routines = _list_special_routines()
        self.assertIn("oiia", routines)

    def test_oiia_gifs_returns_single_gif(self) -> None:
        with patch.object(cube_module, "SPECIAL_GIF_ROOT", self._tmpdir):
            gifs = _list_special_gifs("oiia")
        self.assertEqual([p.name for p in gifs], ["oiia.gif"])


class GetSpecialStatusTests(SpecialModeStateTestCase):
    @patch("server.display.cube._is_cube_display_on", return_value=True)
    def test_reports_running(self, mock_on: Mock) -> None:
        cube_module._SPECIAL_MODE_RUNNING = True
        cube_module._SPECIAL_CURRENT_GIF = "pato-gira.gif"
        cube_module._SPECIAL_CURRENT_ROUTINE = "pato-gira"
        cube_module._SPECIAL_GIFS = ["pato-gira.gif", "pato-gira-rev.gif"]
        cube_module._SPECIAL_INTERVAL = 60
        result = get_special_status()
        self.assertIn("running", result)
        self.assertIn("pato-gira.gif", result)
        self.assertIn("60", result)

    def test_reports_stopped(self) -> None:
        result = get_special_status()
        self.assertIn("stopped", result)

    @patch("server.display.cube._is_cube_display_on", return_value=False)
    def test_reports_paused_when_display_off(self, mock_on: Mock) -> None:
        cube_module._SPECIAL_MODE_RUNNING = True
        result = get_special_status()
        self.assertIn("paused: Cube display is off", result)

    @patch("server.display.cube._is_cube_display_on", return_value=True)
    def test_reports_oiia_routine_running(self, mock_on: Mock) -> None:
        cube_module._SPECIAL_MODE_RUNNING = True
        cube_module._SPECIAL_CURRENT_GIF = "oiia.gif"
        cube_module._SPECIAL_CURRENT_ROUTINE = "oiia"
        cube_module._SPECIAL_GIFS = ["001.gif", "002.gif"]
        cube_module._SPECIAL_INTERVAL = 60
        cube_module._SPECIAL_OIIA_DURATION = 10
        cube_module._SPECIAL_OIIA_RENEW = 600
        result = get_special_status()
        self.assertIn("running", result)
        self.assertIn("Routine: oiia", result)
        self.assertIn("Default gif: oiia.gif", result)
        self.assertIn("001.gif", result)
        self.assertIn("60", result)
        self.assertIn("600", result)

    @patch("server.display.cube._is_cube_display_on", return_value=True)
    def test_reports_oiia_renew_disabled(self, mock_on: Mock) -> None:
        cube_module._SPECIAL_MODE_RUNNING = True
        cube_module._SPECIAL_CURRENT_ROUTINE = "oiia"
        cube_module._SPECIAL_GIFS = ["001.gif"]
        cube_module._SPECIAL_INTERVAL = 60
        cube_module._SPECIAL_OIIA_DURATION = 10
        cube_module._SPECIAL_OIIA_RENEW = 0
        result = get_special_status()
        self.assertIn("auto-renew disabled", result)

    def test_reports_available_routines_includes_oiia(self) -> None:
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        (tmp / "oiia").mkdir()
        (tmp / "oiia" / "oiia.gif").write_bytes(b"x")
        (tmp / "pato-gira").mkdir()
        (tmp / "pato-gira" / "pato-gira.gif").write_bytes(b"y")
        try:
            with patch.object(cube_module, "SPECIAL_GIF_ROOT", tmp):
                result = get_special_status()
            self.assertIn("oiia", result)
            self.assertIn("pato-gira", result)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class StartSpecialRoutineTests(SpecialModeStateTestCase):
    def test_default_is_60_seconds(self) -> None:
        self.assertEqual(SPECIAL_DEFAULT_SECONDS, 60)

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._fetch_cube_gifs", side_effect=[["pato-gira.gif"], ["pato-gira.gif", "pato-gira-rev.gif"]])
    @patch("server.display.cube._upload_cube_image")
    @patch("server.display.cube._fetch_cube_space", return_value=(5*1024*1024, 10*1024*1024))
    @patch("server.display.cube._clear_cube_contents_request", return_value="OK")
    @patch("server.display.cube._fetch_cube_files", side_effect=[[("old.gif", 100)], []])
    @patch("server.display.cube._image_dimensions", return_value=(240, 240))
    @patch("server.display.cube._list_special_gifs")
    @patch("server.display.cube.SPECIAL_GIF_ROOT")
    def test_success_with_default_60s(self, mock_root, mock_list, mock_dims, mock_files, mock_clear, mock_space, mock_upload, mock_gifs, mock_set, mock_thread):
        # setup routine dir mock
        mock_root.__truediv__ = lambda self, x: Path(f"/tmp/{x}")
        # mock gif paths
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        (tmp / "pato-gira.gif").write_bytes(b"a"*100)
        (tmp / "pato-gira-rev.gif").write_bytes(b"b"*100)
        mock_list.return_value = [tmp / "pato-gira.gif", tmp / "pato-gira-rev.gif"]
        with patch.object(cube_module, "SPECIAL_GIF_ROOT", Path(tempfile.gettempdir())):
            with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
                # need to mock _list_special_gifs to return our tmp files directly via patch
                with patch("server.display.cube._list_special_gifs", return_value=[tmp / "pato-gira.gif", tmp / "pato-gira-rev.gif"]):
                    with patch("server.display.cube.SPECIAL_GIF_ROOT", Path(tempfile.gettempdir())):
                        # re-mock existence check
                        with patch("pathlib.Path.is_dir", return_value=True):
                            result = start_special_routine("pato-gira")
                            self.assertEqual(result["status"], "success")
                            self.assertIn("60s", result["message"])
                            self.assertTrue(cube_module._SPECIAL_MODE_RUNNING)
                            self.assertEqual(cube_module._SPECIAL_INTERVAL, 60)
                            mock_thread.assert_called_once()
                            args = mock_thread.call_args[1]["args"]
                            self.assertEqual(args[0], 60)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    @patch("server.display.cube._list_special_gifs", return_value=[])
    def test_returns_error_when_no_gifs(self, mock_list: Mock) -> None:
        with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
            with patch("pathlib.Path.is_dir", return_value=True):
                result = start_special_routine("empty")
                self.assertEqual(result["status"], "error")
                self.assertIn("No .gif files", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch.object(cube_module, "CUBE_BASE_URL", ""):
            result = start_special_routine("pato-gira")
            self.assertEqual(result["status"], "error")
            self.assertIn("CUBE_BASE_URL", result["message"])

    def test_rejects_when_already_running(self) -> None:
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        (tmp / "a.gif").write_bytes(b"dummy")
        cube_module._SPECIAL_MODE_RUNNING = True
        try:
            with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
                with patch("pathlib.Path.is_dir", return_value=True):
                    with patch("server.display.cube._list_special_gifs", return_value=[tmp / "a.gif"]):
                        with patch("server.display.cube._image_dimensions", return_value=(240, 240)):
                            result = start_special_routine("pato-gira")
                            self.assertEqual(result["status"], "error")
                            self.assertIn("already running", result["message"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            cube_module._SPECIAL_MODE_RUNNING = False

    @patch("server.display.cube._fetch_cube_files", side_effect=ConnectionRefusedError("refused"))
    @patch("server.display.cube._list_special_gifs")
    def test_handles_fetch_before_clear_failure(self, mock_list: Mock, mock_files: Mock) -> None:
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        (tmp / "a.gif").write_bytes(b"x")
        mock_list.return_value = [tmp / "a.gif"]
        with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("server.display.cube._image_dimensions", return_value=(240,240)):
                    result = start_special_routine("pato-gira", seconds=10)
                    self.assertEqual(result["status"], "error")
                    self.assertIn("Failed to fetch contents", result["message"])
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


class StartSpecialOiiaTests(SpecialModeStateTestCase):
    """Oiia runs on the unified special state via start_special_routine."""

    def test_oiia_timer_defaults(self) -> None:
        self.assertEqual(OIIA_DEFAULT_EVERY, 60)
        self.assertEqual(OIIA_DEFAULT_DURATION, 10)
        self.assertEqual(OIIA_DEFAULT_RENEW, 600)

    def _make_oiia_dir(self) -> Path:
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        (tmp / "oiia.gif").write_bytes(b"oiia-bytes")
        (tmp / "random").mkdir()
        return tmp

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._fetch_cube_gifs", return_value=["oiia.gif"])
    @patch("server.display.cube._upload_cube_image")
    @patch("server.display.cube._fetch_cube_space", return_value=(5 * 1024 * 1024, 10 * 1024 * 1024))
    @patch("server.display.cube._clear_cube_contents_request", return_value="OK")
    @patch("server.display.cube._fetch_cube_files", side_effect=[[("old.gif", 100)], []])
    @patch("server.display.cube._image_dimensions", return_value=(240, 240))
    @patch("server.display.cube._oiia_fill_randoms", return_value=["001.gif", "002.gif"])
    def test_special_oiia_starts_on_special_state(
        self, mock_fill, mock_dims, mock_files, mock_clear, mock_space,
        mock_upload, mock_gifs, mock_set, mock_thread,
    ) -> None:
        import shutil
        tmp = self._make_oiia_dir()
        try:
            with patch.object(cube_module, "OIIA_DIR", tmp):
                with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
                    result = start_special_routine("oiia", every=60, duration=10, renew=600)
            self.assertEqual(result["status"], "success")
            self.assertIn("oiia.gif", result["message"])
            self.assertIn("2 random", result["message"])
            self.assertTrue(cube_module._SPECIAL_MODE_RUNNING)
            self.assertEqual(cube_module._SPECIAL_CURRENT_ROUTINE, "oiia")
            self.assertEqual(cube_module._SPECIAL_CURRENT_GIF, "oiia.gif")
            self.assertEqual(cube_module._SPECIAL_GIFS, ["001.gif", "002.gif"])
            self.assertEqual(cube_module._SPECIAL_INTERVAL, 60)
            self.assertEqual(cube_module._SPECIAL_OIIA_DURATION, 10)
            self.assertEqual(cube_module._SPECIAL_OIIA_RENEW, 600)
            mock_upload.assert_called_once()  # only the default gif is uploaded at start
            mock_thread.assert_called_once()
            args = mock_thread.call_args[1]["args"]
            self.assertEqual(args, (60, 10, 600))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_special_oiia_rejects_duration_not_less_than_every(self) -> None:
        with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
            result = start_special_routine("oiia", every=10, duration=10)
            self.assertEqual(result["status"], "error")
            self.assertIn("must be less than", result["message"])
            self.assertFalse(cube_module._SPECIAL_MODE_RUNNING)

    def test_special_oiia_rejects_when_already_running(self) -> None:
        cube_module._SPECIAL_MODE_RUNNING = True
        with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
            result = start_special_routine("oiia")
            self.assertEqual(result["status"], "error")
            self.assertIn("already running", result["message"])

    def test_special_oiia_returns_error_when_default_gif_missing(self) -> None:
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        try:
            with patch.object(cube_module, "OIIA_DIR", tmp):
                with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
                    result = start_special_routine("oiia")
            self.assertEqual(result["status"], "error")
            self.assertIn("Default oiia gif not found", result["message"])
            self.assertFalse(cube_module._SPECIAL_MODE_RUNNING)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class StopSpecialRoutineTests(SpecialModeStateTestCase):
    def test_stops_when_running(self) -> None:
        cube_module._SPECIAL_MODE_RUNNING = True
        cube_module._SPECIAL_CURRENT_GIF = "pato-gira.gif"
        result = stop_special_routine()
        self.assertEqual(result["status"], "success")
        self.assertIn("stopped", result["message"].lower())
        self.assertFalse(cube_module._SPECIAL_MODE_RUNNING)

    def test_succeeds_when_not_running(self) -> None:
        result = stop_special_routine()
        self.assertEqual(result["status"], "success")
        self.assertIn("not running", result["message"])

    def test_stops_oiia_when_running(self) -> None:
        cube_module._SPECIAL_MODE_RUNNING = True
        cube_module._SPECIAL_CURRENT_ROUTINE = "oiia"
        cube_module._SPECIAL_CURRENT_GIF = "001.gif"
        result = stop_special_routine()
        self.assertEqual(result["status"], "success")
        self.assertIn("stopped", result["message"].lower())
        self.assertIn("001.gif", result["message"])
        self.assertFalse(cube_module._SPECIAL_MODE_RUNNING)


class SpecialLoopTests(SpecialModeStateTestCase):
    @patch("server.display.cube.time.sleep")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    def test_loop_switches_every_interval_simple_timer(self, mock_set: Mock, mock_sleep: Mock) -> None:
        cube_module._SPECIAL_MODE_RUNNING = True
        cube_module._SPECIAL_CURRENT_GIF = "pato-gira.gif"
        # make sleep count and stop after 2 intervals
        counts = {"c": 0}
        def sleep_side(sec):
            counts["c"] += 1
            if counts["c"] >= 20:  # 10+10
                cube_module._SPECIAL_MODE_RUNNING = False
        mock_sleep.side_effect = sleep_side
        _special_loop(10, ["pato-gira.gif", "pato-gira-rev.gif"])
        # should have switched at least once
        self.assertTrue(mock_set.called)
        called_gifs = [c.args[0] for c in mock_set.call_args_list]
        # first switch should be rev, second back to plain
        self.assertIn("pato-gira-rev.gif", called_gifs)
        self.assertFalse(cube_module._SPECIAL_MODE_RUNNING)


class SpecialStopOnSetTests(SpecialModeStateTestCase):
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._stop_special_mode", return_value=(True, "pato-gira.gif"))
    @patch("server.display.cube._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube._fetch_cube_gifs", return_value=["test.gif", "pato-gira.gif"])
    def test_set_cube_gif_stops_special(self, mock_gifs, mock_stop_random, mock_stop_image, mock_stop_special, mock_set):
        from server.display.cube import set_cube_gif
        with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
            result = set_cube_gif("pato-gira.gif")
            self.assertEqual(result["status"], "success")
            mock_stop_special.assert_called_once()
            self.assertIn("Special routine stopped", result["message"])

    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._stop_special_mode", return_value=(True, "pato-gira.gif"))
    @patch("server.display.cube._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube._fetch_cube_gifs", return_value=["photo.jpg"])
    @patch("server.display.cube._upload_cube_image")
    def test_show_gallery_image_stops_special(self, mock_upload, mock_gifs, mock_stop_random, mock_stop_image, mock_stop_special, mock_set):
        from server.display.cube import show_gallery_image
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        # create dummy jpeg
        from io import BytesIO
        from PIL import Image
        buf = BytesIO()
        Image.new("RGB", (240, 240)).save(buf, format="JPEG")
        (tmp / "photo.jpg").write_bytes(buf.getvalue())
        with patch.object(cube_module, "RANDOM_IMAGE_DIR", tmp):
            with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
                with patch("server.display.cube._fetch_cube_space", return_value=(5*1024*1024, 10*1024*1024)):
                    result = show_gallery_image("photo.jpg")
                    self.assertEqual(result["status"], "success")
                    mock_stop_special.assert_called_once()
                    self.assertIn("Special routine stopped", result["message"])
        shutil.rmtree(tmp, ignore_errors=True)

    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube._stop_special_mode", return_value=(True, "pato-gira.gif"))
    @patch("server.display.cube._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube._fetch_cube_gifs", return_value=["tmp.gif"])
    @patch("server.display.cube._upload_cube_image")
    def test_show_gallery_gif_stops_special(self, mock_upload, mock_gifs, mock_stop_random, mock_stop_image, mock_stop_special, mock_set):
        from server.display.cube import show_gallery_gif
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        from io import BytesIO
        from PIL import Image
        buf = BytesIO()
        Image.new("RGB", (240, 240)).save(buf, format="GIF")
        (tmp / "anim.gif").write_bytes(buf.getvalue())
        with patch.object(cube_module, "RANDOM_GIF_DIR", tmp):
            with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
                with patch("server.display.cube._fetch_cube_space", return_value=(5*1024*1024, 10*1024*1024)):
                    result = show_gallery_gif("anim.gif")
                    self.assertEqual(result["status"], "success")
                    mock_stop_special.assert_called_once()
                    self.assertIn("Special routine stopped", result["message"])
        shutil.rmtree(tmp, ignore_errors=True)

    @patch("server.display.cube._suspend_special_mode", return_value=True)
    @patch("server.display.cube._suspend_image_mode", return_value=False)
    @patch("server.display.cube._suspend_random_mode", return_value=False)
    @patch("server.display.cube.upload_cube_image", return_value={"status": "success", "message": "ok"})
    @patch("server.display.cube._fetch_cube_current_gif", return_value="/image/old.gif")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch("server.display.cube.threading.Thread")
    def test_show_temporary_gif_suspends_special(self, mock_thread, mock_set, mock_fetch, mock_upload, mock_susp_rand, mock_susp_img, mock_susp_special):
        from server.display.cube import show_temporary_gif
        import base64, tempfile
        from PIL import Image
        from io import BytesIO
        buf = BytesIO()
        Image.new("RGB", (240, 240)).save(buf, format="GIF")
        data = base64.b64encode(buf.getvalue()).decode()
        # reset the temporary-gif flag: a previous test module may have left it
        # set since the background restore thread is mocked and never runs.
        with cube_module._TEMP_GIF_LOCK:
            cube_module._TEMP_GIF_RUNNING = False
        with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
            result = show_temporary_gif(data, "tmp.gif", seconds=5)
            self.assertEqual(result["status"], "success")
            mock_susp_special.assert_called_once()
        with cube_module._TEMP_GIF_LOCK:
            cube_module._TEMP_GIF_RUNNING = False

    @patch("server.display.cube._stop_special_mode", return_value=(True, "pato-gira.gif"))
    @patch("server.display.cube._stop_image_mode", return_value=(False, None))
    @patch("server.display.cube._run_random_cycle", return_value=(True, "first.gif"))
    @patch("server.display.cube._list_local_gifs", return_value=[Path("first.gif")])
    @patch("server.display.cube.threading.Thread")
    def test_start_random_gifs_stops_special(self, mock_thread, mock_list, mock_cycle, mock_stop_img, mock_stop_special):
        from server.display.cube import start_random_gifs
        with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
            result = start_random_gifs(seconds=300)
            self.assertEqual(result["status"], "success")
            mock_stop_special.assert_called_once()
            self.assertIn("Special routine stopped", result["message"])

    @patch("server.display.cube._stop_special_mode", return_value=(True, "pato-gira.gif"))
    @patch("server.display.cube._stop_random_mode", return_value=(False, None))
    @patch("server.display.cube._run_random_image_cycle", return_value=(True, "first.jpg"))
    @patch("server.display.cube._list_local_images", return_value=[Path("first.jpg")])
    @patch("server.display.cube.threading.Thread")
    def test_start_random_images_stops_special(self, mock_thread, mock_list, mock_cycle, mock_stop_rand, mock_stop_special):
        from server.display.cube import start_random_images
        with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
            result = start_random_images(seconds=300)
            self.assertEqual(result["status"], "success")
            mock_stop_special.assert_called_once()
            self.assertIn("Special routine stopped", result["message"])


class ListOiiaRandomGifsTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmpdir = Path(tempfile.mkdtemp())
        random_dir = self._tmpdir / "random"
        random_dir.mkdir(parents=True)
        (random_dir / "001.gif").write_bytes(b"a")
        (random_dir / "002.gif").write_bytes(b"b")
        (random_dir / "notes.txt").write_bytes(b"c")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_lists_only_gifs_sorted(self) -> None:
        with patch.object(cube_module, "OIIA_RANDOM_DIR", self._tmpdir / "random"):
            gifs = _list_oiia_random_gifs()
        self.assertEqual([p.name for p in gifs], ["001.gif", "002.gif"])

    def test_returns_empty_when_dir_missing(self) -> None:
        with patch.object(cube_module, "OIIA_RANDOM_DIR", self._tmpdir / "nope"):
            self.assertEqual(_list_oiia_random_gifs(), [])


class OiiaFillTests(SpecialModeStateTestCase):
    @patch("server.display.cube._fetch_cube_gifs", return_value=["a.gif"])
    @patch("server.display.cube._upload_cube_image")
    @patch("server.display.cube._cube_free_space_rejection", side_effect=[None, "full"])
    @patch("server.display.cube._image_dimensions", return_value=(240, 240))
    @patch("server.display.cube.random.shuffle", side_effect=lambda items: None)
    def test_fill_stops_when_cube_full(
        self, mock_shuffle, mock_dims, mock_space, mock_upload, mock_gifs
    ) -> None:
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        (tmp / "a.gif").write_bytes(b"x" * 10)
        (tmp / "b.gif").write_bytes(b"y" * 10)
        paths = [tmp / "a.gif", tmp / "b.gif"]
        cube_module._SPECIAL_MODE_RUNNING = True
        try:
            with patch("server.display.cube._list_oiia_random_gifs", return_value=list(paths)):
                uploaded = _oiia_fill_randoms()
            self.assertEqual(uploaded, ["a.gif"])
            mock_upload.assert_called_once()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @patch("server.display.cube._fetch_cube_gifs", return_value=["b.gif"])
    @patch("server.display.cube._upload_cube_image")
    @patch("server.display.cube._cube_free_space_rejection", side_effect=["too big", None])
    @patch("server.display.cube._image_dimensions", return_value=(240, 240))
    @patch("server.display.cube.random.shuffle", side_effect=lambda items: None)
    def test_fill_skips_unfit_gif_and_packs_smaller(
        self, mock_shuffle, mock_dims, mock_space, mock_upload, mock_gifs
    ) -> None:
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        (tmp / "a.gif").write_bytes(b"x" * 10)
        (tmp / "b.gif").write_bytes(b"y" * 10)
        paths = [tmp / "a.gif", tmp / "b.gif"]
        cube_module._SPECIAL_MODE_RUNNING = True
        try:
            with patch("server.display.cube._list_oiia_random_gifs", return_value=list(paths)):
                uploaded = _oiia_fill_randoms()
            self.assertEqual(uploaded, ["b.gif"])
            mock_upload.assert_called_once()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @patch("server.display.cube._delete_cube_file")
    @patch("server.display.cube._oiia_fill_randoms", return_value=["n1.gif"])
    def test_refresh_deletes_old_and_swaps_batch(self, mock_fill, mock_delete) -> None:
        cube_module._SPECIAL_MODE_RUNNING = True
        cube_module._SPECIAL_GIFS = ["o1.gif", "o2.gif"]
        try:
            result = _oiia_refresh_randoms()
            self.assertEqual(result, ["n1.gif"])
            self.assertEqual(cube_module._SPECIAL_GIFS, ["n1.gif"])
            deleted = [c.args[0] for c in mock_delete.call_args_list]
            self.assertEqual(sorted(deleted), ["o1.gif", "o2.gif"])
            mock_fill.assert_called_once_with(prefer_exclude={"o1.gif", "o2.gif"})
        finally:
            cube_module._SPECIAL_MODE_RUNNING = False


class OiiaLoopTests(SpecialModeStateTestCase):
    @patch("server.display.cube.random.choice", return_value="r2.gif")
    @patch("server.display.cube._oiia_refresh_randoms")
    @patch("server.display.cube._is_cube_display_on", return_value=True)
    @patch("server.display.cube.time.sleep")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    def test_loop_picks_random_then_default(
        self, mock_set: Mock, mock_sleep: Mock, mock_on: Mock,
        mock_refresh: Mock, mock_choice: Mock,
    ) -> None:
        cube_module._SPECIAL_MODE_RUNNING = True
        cube_module._SPECIAL_GIFS = ["r1.gif", "r2.gif"]
        counts = {"c": 0}

        def sleep_side(sec):
            counts["c"] += 1
            if counts["c"] >= 4:  # every=2 ticks + duration=1 tick + 1 extra
                cube_module._SPECIAL_MODE_RUNNING = False

        mock_sleep.side_effect = sleep_side
        _oiia_loop(2, 1, 0)
        called = [c.args[0] for c in mock_set.call_args_list]
        self.assertEqual(called[0], "r2.gif")
        self.assertIn(OIIA_DEFAULT_GIF_NAME, called)
        mock_choice.assert_called_with(["r1.gif", "r2.gif"])
        mock_refresh.assert_not_called()  # renew=0 disables auto-renew
        self.assertFalse(cube_module._SPECIAL_MODE_RUNNING)
        self.assertEqual(cube_module._SPECIAL_CURRENT_GIF, OIIA_DEFAULT_GIF_NAME)

    @patch("server.display.cube.time.monotonic", side_effect=[0, 10000, 10000])
    @patch("server.display.cube._oiia_refresh_randoms")
    @patch("server.display.cube._is_cube_display_on", return_value=True)
    @patch("server.display.cube.time.sleep")
    @patch("server.display.cube._set_cube_gif", return_value="OK")
    def test_loop_renews_batch_on_timer(
        self, mock_set: Mock, mock_sleep: Mock, mock_on: Mock,
        mock_refresh: Mock, mock_monotonic: Mock,
    ) -> None:
        def refresh_side():
            # mirror the real refresh: swap in a fresh batch
            cube_module._SPECIAL_GIFS = ["r2.gif"]
            return ["r2.gif"]

        mock_refresh.side_effect = refresh_side
        cube_module._SPECIAL_MODE_RUNNING = True
        cube_module._SPECIAL_GIFS = ["r1.gif"]
        counts = {"c": 0}

        def sleep_side(sec):
            counts["c"] += 1
            if counts["c"] >= 3:  # every=1 + duration=1 + 1 extra
                cube_module._SPECIAL_MODE_RUNNING = False

        mock_sleep.side_effect = sleep_side
        _oiia_loop(1, 1, 60)
        mock_refresh.assert_called_once()
        self.assertEqual(cube_module._SPECIAL_GIFS, ["r2.gif"])


class WaitPollIntervalTests(unittest.TestCase):
    def test_default_polls_display_every_second(self) -> None:
        ticks = {"n": 0}
        with patch("server.display.cube.time.sleep", side_effect=lambda s: ticks.__setitem__("n", ticks["n"] + 1)):
            with patch("server.display.cube._is_cube_display_on", return_value=True) as mock_on:
                _wait_between_cycles(5, lambda: ticks["n"] <= 5, lambda: False)
        self.assertEqual(ticks["n"], 5)
        self.assertEqual(mock_on.call_count, 5)

    def test_oiia_interval_polls_display_rarely(self) -> None:
        ticks = {"n": 0}
        with patch("server.display.cube.time.sleep", side_effect=lambda s: ticks.__setitem__("n", ticks["n"] + 1)):
            with patch("server.display.cube._is_cube_display_on", return_value=True) as mock_on:
                _wait_between_cycles(100, lambda: ticks["n"] < 35, lambda: False, OIIA_DISPLAY_POLL_SECONDS)
        self.assertEqual(ticks["n"], 35)
        # first tick + every OIIA_DISPLAY_POLL_SECONDS: ticks 1, 16, 31
        self.assertEqual(mock_on.call_count, 3)

    def test_stop_still_reacts_within_one_second(self) -> None:
        ticks = {"n": 0}

        def running():
            return ticks["n"] < 2

        with patch("server.display.cube.time.sleep", side_effect=lambda s: ticks.__setitem__("n", ticks["n"] + 1)):
            with patch("server.display.cube._is_cube_display_on", return_value=True):
                _wait_between_cycles(100, running, lambda: False, OIIA_DISPLAY_POLL_SECONDS)
        self.assertEqual(ticks["n"], 2)


if __name__ == "__main__":
    unittest.main()
