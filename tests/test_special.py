import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from server.display import cube as cube_module
from server.display.cube import (
    _list_special_gifs,
    _list_special_routines,
    _special_loop,
    get_special_status,
    start_special_routine,
    stop_special_routine,
    SPECIAL_GIF_ROOT,
    SPECIAL_DEFAULT_SECONDS,
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
        )
        cube_module._SPECIAL_MODE_RUNNING = False
        cube_module._SPECIAL_MODE_SUSPENDED = False
        cube_module._SPECIAL_CURRENT_GIF = None
        cube_module._SPECIAL_CURRENT_ROUTINE = None
        cube_module._SPECIAL_GIFS = None
        cube_module._SPECIAL_INTERVAL = None

    def tearDown(self) -> None:
        (
            cube_module._SPECIAL_MODE_RUNNING,
            cube_module._SPECIAL_MODE_SUSPENDED,
            cube_module._SPECIAL_CURRENT_GIF,
            cube_module._SPECIAL_CURRENT_ROUTINE,
            cube_module._SPECIAL_GIFS,
            cube_module._SPECIAL_INTERVAL,
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
        with patch.object(cube_module, "CUBE_BASE_URL", "http://fake"):
            result = show_temporary_gif(data, "tmp.gif", seconds=5)
            self.assertEqual(result["status"], "success")
            mock_susp_special.assert_called_once()

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


if __name__ == "__main__":
    unittest.main()
