import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from server.display import cube as cube_module
from server.display.cube import (
    _list_local_gifs,
    _pick_random_gif,
    _sleep_interruptible,
    _run_random_cycle,
    _random_gif_loop,
    get_random_gif_status,
    start_random_gifs,
    stop_random_gifs,
    RANDOM_GIF_DIR,
    RANDOM_GIF_NAME,
)


class RandomModeStateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._originals = (
            cube_module._RANDOM_MODE_RUNNING,
            cube_module._RANDOM_MODE_SUSPENDED,
            cube_module._RANDOM_CURRENT_GIF,
        )
        cube_module._RANDOM_MODE_RUNNING = False
        cube_module._RANDOM_MODE_SUSPENDED = False
        cube_module._RANDOM_CURRENT_GIF = None

    def tearDown(self) -> None:
        (
            cube_module._RANDOM_MODE_RUNNING,
            cube_module._RANDOM_MODE_SUSPENDED,
            cube_module._RANDOM_CURRENT_GIF,
        ) = self._originals


class ListLocalGifsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = Path(__import__("tempfile").mkdtemp())
        (self._tmpdir / "a.gif").write_bytes(b"a")
        (self._tmpdir / "b.GIF").write_bytes(b"b")
        (self._tmpdir / "c.jpg").write_bytes(b"c")
        (self._tmpdir / "d.txt").write_bytes(b"d")

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_lists_only_gif_files_sorted(self) -> None:
        with patch.object(cube_module, "RANDOM_GIF_DIR", self._tmpdir):
            gifs = _list_local_gifs()

        self.assertEqual([gif.name for gif in gifs], ["a.gif", "b.GIF"])

    def test_returns_empty_when_dir_missing(self) -> None:
        with patch.object(cube_module, "RANDOM_GIF_DIR", self._tmpdir / "missing"):
            gifs = _list_local_gifs()

        self.assertEqual(gifs, [])

    def test_default_dir_is_media_video_gifs(self) -> None:
        self.assertEqual(RANDOM_GIF_DIR.name, "gifs")
        self.assertTrue(RANDOM_GIF_DIR.is_dir())


class PickRandomGifTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gifs = [Path("a.gif"), Path("b.gif"), Path("c.gif")]

    @patch("server.display.cube._list_local_gifs")
    def test_picks_one_of_available_gifs(self, mock_list: Mock) -> None:
        mock_list.return_value = self.gifs

        picked = _pick_random_gif()

        self.assertIn(picked, self.gifs)

    @patch("server.display.cube._list_local_gifs")
    def test_avoids_excluded_gif_when_alternatives_exist(self, mock_list: Mock) -> None:
        mock_list.return_value = self.gifs

        for _ in range(20):
            self.assertNotEqual(_pick_random_gif("b.gif"), Path("b.gif"))

    @patch("server.display.cube._list_local_gifs")
    def test_falls_back_to_excluded_gif_when_only_option(self, mock_list: Mock) -> None:
        mock_list.return_value = [Path("only.gif")]

        picked = _pick_random_gif("only.gif")

        self.assertEqual(picked, Path("only.gif"))

    @patch("server.display.cube._list_local_gifs", return_value=[])
    def test_returns_none_when_no_gifs(self, mock_list: Mock) -> None:
        self.assertIsNone(_pick_random_gif())


class SuspendResumeRandomModeTests(RandomModeStateTestCase):
    def test_suspend_returns_true_and_flags_when_running(self) -> None:
        cube_module._RANDOM_MODE_RUNNING = True

        self.assertTrue(cube_module._suspend_random_mode())
        self.assertTrue(cube_module._RANDOM_MODE_SUSPENDED)
        self.assertTrue(cube_module._RANDOM_MODE_RUNNING)

    def test_suspend_returns_false_when_not_running(self) -> None:
        self.assertFalse(cube_module._suspend_random_mode())
        self.assertFalse(cube_module._RANDOM_MODE_SUSPENDED)

    def test_resume_clears_flag(self) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        cube_module._suspend_random_mode()

        cube_module._resume_random_mode()

        self.assertFalse(cube_module._RANDOM_MODE_SUSPENDED)
        self.assertTrue(cube_module._RANDOM_MODE_RUNNING)

    def test_stop_clears_suspension_too(self) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        cube_module._RANDOM_CURRENT_GIF = "test.gif"
        cube_module._suspend_random_mode()

        was_running, current = cube_module._stop_random_mode()

        self.assertTrue(was_running)
        self.assertEqual(current, "test.gif")
        self.assertFalse(cube_module._RANDOM_MODE_RUNNING)
        self.assertFalse(cube_module._RANDOM_MODE_SUSPENDED)


class IsCubeDisplayOnTests(unittest.TestCase):
    @patch("server.display.cube._fetch_cube_brightness", return_value=50)
    def test_true_when_brightness_above_zero(self, mock_fetch: Mock) -> None:
        self.assertTrue(cube_module._is_cube_display_on())

    @patch("server.display.cube._fetch_cube_brightness", return_value=0)
    def test_false_when_display_off(self, mock_fetch: Mock) -> None:
        self.assertFalse(cube_module._is_cube_display_on())

    @patch(
        "server.display.cube._fetch_cube_brightness",
        side_effect=ConnectionRefusedError("connection refused"),
    )
    def test_false_when_device_unreachable(self, mock_fetch: Mock) -> None:
        self.assertFalse(cube_module._is_cube_display_on())


class SleepInterruptibleTests(RandomModeStateTestCase):
    @patch("server.display.cube._is_cube_display_on", return_value=True)
    @patch("server.display.cube.time.sleep")
    def test_sleeps_in_one_second_steps_when_display_on(
        self, mock_sleep: Mock, mock_on: Mock
    ) -> None:
        cube_module._RANDOM_MODE_RUNNING = True

        _sleep_interruptible(3)

        mock_sleep.assert_has_calls([call(1), call(1), call(1)])
        self.assertEqual(mock_sleep.call_count, 3)
        mock_on.assert_called()

    @patch("server.display.cube._is_cube_display_on", return_value=True)
    @patch("server.display.cube.time.sleep")
    def test_exits_early_when_mode_is_stopped(self, mock_sleep: Mock, mock_on: Mock) -> None:
        cube_module._RANDOM_MODE_RUNNING = True

        def _stop(_: float) -> None:
            cube_module._RANDOM_MODE_RUNNING = False

        mock_sleep.side_effect = _stop

        _sleep_interruptible(60)

        mock_sleep.assert_called_once_with(1)
        mock_on.assert_not_called()

    @patch("server.display.cube.time.sleep")
    @patch("server.display.cube._is_cube_display_on", return_value=False)
    def test_pauses_countdown_while_display_is_off(
        self, mock_on: Mock, mock_sleep: Mock
    ) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        # Display stays off for the first two checks, then turns back on.
        states = iter([False, False, True, True])
        mock_on.side_effect = lambda: next(states)

        _sleep_interruptible(2)

        # Two extra seconds elapsed while paused before finishing the wait.
        self.assertEqual(mock_sleep.call_count, 4)

    @patch("server.display.cube._is_cube_display_on", return_value=True)
    @patch("server.display.cube.time.sleep")
    def test_pauses_countdown_while_suspended(
        self, mock_sleep: Mock, mock_on: Mock
    ) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        cube_module._RANDOM_MODE_SUSPENDED = True

        checks = {"count": 0}

        def _sleep(_: float) -> None:
            checks["count"] += 1
            if checks["count"] >= 3:
                cube_module._RANDOM_MODE_SUSPENDED = False

        mock_sleep.side_effect = _sleep

        _sleep_interruptible(1)

        # Two seconds elapsed while suspended before counting the last one.
        self.assertEqual(mock_sleep.call_count, 3)
        self.assertFalse(cube_module._RANDOM_MODE_SUSPENDED)


class RunRandomCycleTests(RandomModeStateTestCase):
    def setUp(self) -> None:
        super().setUp()
        import shutil
        import tempfile

        self._tmpdir = Path(tempfile.mkdtemp())
        self._gif_path = self._tmpdir / "picked.gif"
        self._gif_path.write_bytes(b"gifdata")

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmpdir, ignore_errors=True)
        super().tearDown()

    @patch("server.display.cube._set_cube_gif", return_value="OK")
    @patch(
        "server.display.cube.upload_cube_image",
        return_value={"status": "success", "message": "uploaded"},
    )
    @patch("server.display.cube._pick_random_gif")
    def test_uploads_and_displays_as_random_gif(
        self, mock_pick: Mock, mock_upload: Mock, mock_set: Mock
    ) -> None:
        import base64

        mock_pick.return_value = self._gif_path

        ok, value = _run_random_cycle("previous.gif")

        self.assertTrue(ok)
        self.assertEqual(value, "picked.gif")
        mock_pick.assert_called_once_with("previous.gif")
        encoded = mock_upload.call_args[0][0]
        filename = mock_upload.call_args[0][1]
        self.assertEqual(filename, RANDOM_GIF_NAME)
        self.assertEqual(base64.b64decode(encoded), b"gifdata")
        mock_set.assert_called_once_with(RANDOM_GIF_NAME)

    @patch("server.display.cube.upload_cube_image")
    @patch("server.display.cube._pick_random_gif", return_value=None)
    def test_fails_when_no_gifs_available(self, mock_pick: Mock, mock_upload: Mock) -> None:
        ok, value = _run_random_cycle()

        self.assertFalse(ok)
        self.assertIn("No .gif files found", value)
        mock_upload.assert_not_called()

    @patch("server.display.cube._set_cube_gif")
    @patch(
        "server.display.cube.upload_cube_image",
        return_value={"status": "error", "message": "Image must be 240x240"},
    )
    @patch("server.display.cube._pick_random_gif")
    def test_propagates_upload_error_message(
        self, mock_pick: Mock, mock_upload: Mock, mock_set: Mock
    ) -> None:
        mock_pick.return_value = self._gif_path

        ok, value = _run_random_cycle()

        self.assertFalse(ok)
        self.assertIn("Image must be 240x240", value)
        mock_set.assert_not_called()

    @patch("server.display.cube._set_cube_gif", return_value="FAIL")
    @patch(
        "server.display.cube.upload_cube_image",
        return_value={"status": "success", "message": "uploaded"},
    )
    @patch("server.display.cube._pick_random_gif")
    def test_fails_when_cube_refuses_display(
        self, mock_pick: Mock, mock_upload: Mock, mock_set: Mock
    ) -> None:
        mock_pick.return_value = self._gif_path

        ok, value = _run_random_cycle()

        self.assertFalse(ok)
        self.assertIn("Cube refused to display random.gif", value)

    @patch("server.display.cube._pick_random_gif", side_effect=RuntimeError("boom"))
    def test_converts_exceptions_into_error_message(self, mock_pick: Mock) -> None:
        ok, value = _run_random_cycle()

        self.assertFalse(ok)
        self.assertEqual(value, "boom")


class GetRandomGifStatusTests(RandomModeStateTestCase):
    @patch("server.display.cube._is_cube_display_on", return_value=True)
    def test_reports_running_with_current_gif(self, mock_on: Mock) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        cube_module._RANDOM_CURRENT_GIF = "test.gif"

        result = get_random_gif_status()

        self.assertIn("Random gif mode: running", result)
        self.assertIn(f"Current temporary gif: test.gif (uploaded as {RANDOM_GIF_NAME})", result)

    def test_reports_stopped_without_current_gif(self) -> None:
        result = get_random_gif_status()

        self.assertIn("Random gif mode: stopped", result)
        self.assertIn("No temporary gif has been shown yet.", result)

    @patch("server.display.cube._is_cube_display_on", return_value=False)
    def test_reports_paused_when_display_off(self, mock_on: Mock) -> None:
        cube_module._RANDOM_MODE_RUNNING = True

        result = get_random_gif_status()

        self.assertIn("running (paused: Cube display is off)", result)

    @patch("server.display.cube._is_cube_display_on", return_value=True)
    def test_reports_suspended_while_temporary_gif_shown(self, mock_on: Mock) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        cube_module._RANDOM_MODE_SUSPENDED = True

        result = get_random_gif_status()

        self.assertIn("running (suspended: temporary gif being shown)", result)


class StartRandomGifsTests(RandomModeStateTestCase):
    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._run_random_cycle", return_value=(True, "first.gif"))
    @patch("server.display.cube._list_local_gifs", return_value=[Path("first.gif")])
    def test_shows_first_gif_and_starts_background_loop(
        self, mock_list: Mock, mock_cycle: Mock, mock_thread_cls: Mock
    ) -> None:
        result = start_random_gifs()

        self.assertEqual(result["status"], "success")
        self.assertIn("first.gif is displayed as random.gif", result["message"])
        self.assertIn("every 60 seconds", result["message"])
        self.assertEqual(cube_module._RANDOM_CURRENT_GIF, "first.gif")
        self.assertTrue(cube_module._RANDOM_MODE_RUNNING)
        mock_cycle.assert_called_once_with(None)
        mock_thread_cls.assert_called_once_with(
            target=cube_module._random_gif_loop, args=(60, "first.gif"), daemon=True
        )
        mock_thread_cls.return_value.start.assert_called_once()

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._run_random_cycle", return_value=(True, "x.gif"))
    @patch("server.display.cube._list_local_gifs", return_value=[Path("x.gif")])
    def test_clamps_seconds_to_valid_range(
        self, mock_list: Mock, mock_cycle: Mock, mock_thread_cls: Mock
    ) -> None:
        low = start_random_gifs(seconds=0)
        cube_module._RANDOM_MODE_RUNNING = False
        high = start_random_gifs(seconds=99999)

        self.assertIn("every 5 seconds", low["message"])
        self.assertIn("every 3600 seconds", high["message"])
        thread_args = [
            c.kwargs["args"]
            for c in mock_thread_cls.call_args_list
            if "args" in c.kwargs
        ]
        self.assertEqual(thread_args, [(5, "x.gif"), (3600, "x.gif")])

    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._run_random_cycle", return_value=(True, "first.gif"))
    @patch("server.display.cube._list_local_gifs", return_value=[Path("first.gif")])
    def test_resets_suspension_when_starting(
        self, mock_list: Mock, mock_cycle: Mock, mock_thread_cls: Mock
    ) -> None:
        cube_module._RANDOM_MODE_SUSPENDED = True

        result = start_random_gifs()

        self.assertEqual(result["status"], "success")
        self.assertFalse(cube_module._RANDOM_MODE_SUSPENDED)

    @patch("server.display.cube._run_random_cycle")
    @patch("server.display.cube._list_local_gifs", return_value=[Path("x.gif")])
    def test_rejects_when_already_running(self, mock_list: Mock, mock_cycle: Mock) -> None:
        cube_module._RANDOM_MODE_RUNNING = True

        result = start_random_gifs()

        self.assertEqual(result["status"], "error")
        self.assertIn("already running", result["message"])
        mock_cycle.assert_not_called()

    def test_returns_error_when_not_configured(self) -> None:
        with patch.object(cube_module, "CUBE_BASE_URL", ""):
            result = start_random_gifs()

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])

    @patch("server.display.cube._list_local_gifs", return_value=[])
    def test_returns_error_when_no_local_gifs(self, mock_list: Mock) -> None:
        result = start_random_gifs()

        self.assertEqual(result["status"], "error")
        self.assertIn("No .gif files found", result["message"])

    @patch("server.display.cube.threading.Thread")
    @patch(
        "server.display.cube._run_random_cycle",
        return_value=(False, "Cube refused to display random.gif"),
    )
    @patch("server.display.cube._list_local_gifs", return_value=[Path("x.gif")])
    def test_releases_flag_when_first_cycle_fails(
        self, mock_list: Mock, mock_cycle: Mock, mock_thread_cls: Mock
    ) -> None:
        result = start_random_gifs()

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to display the first random gif", result["message"])
        self.assertFalse(cube_module._RANDOM_MODE_RUNNING)
        mock_thread_cls.assert_not_called()


class StopRandomGifsTests(RandomModeStateTestCase):
    @patch("server.display.cube.threading.Thread")
    @patch("server.display.cube._run_random_cycle", return_value=(True, "shown.gif"))
    @patch("server.display.cube._list_local_gifs", return_value=[Path("shown.gif")])
    def _start(self, mock_list: Mock, mock_cycle: Mock, mock_thread_cls: Mock) -> None:
        start_random_gifs()

    def test_stops_and_reports_remaining_gif(self) -> None:
        self._start()
        cube_module._RANDOM_CURRENT_GIF = "shown.gif"

        result = stop_random_gifs()

        self.assertEqual(result["status"], "success")
        self.assertIn("Random gif mode stopped.", result["message"])
        self.assertIn("shown.gif (random.gif) remains displayed", result["message"])
        self.assertFalse(cube_module._RANDOM_MODE_RUNNING)

    def test_succeeds_even_when_not_running(self) -> None:
        result = stop_random_gifs()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Random gif mode is not running.")


class RandomGifLoopTests(RandomModeStateTestCase):
    @patch("server.display.cube._run_random_cycle")
    @patch("server.display.cube._is_cube_display_on", return_value=True)
    @patch("server.display.cube.time.sleep")
    def test_runs_requested_number_of_cycles_then_exits(
        self, mock_sleep: Mock, mock_on: Mock, mock_cycle: Mock
    ) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        mock_cycle.side_effect = [(True, "second.gif"), (True, "third.gif")]

        sleeps = {"count": 0}

        def _sleep(_: float) -> None:
            sleeps["count"] += 1
            if sleeps["count"] >= 3:
                cube_module._RANDOM_MODE_RUNNING = False

        mock_sleep.side_effect = _sleep

        _random_gif_loop(1, "first.gif")

        self.assertEqual(mock_cycle.call_count, 2)
        mock_cycle.assert_has_calls([call("first.gif"), call("second.gif")])
        self.assertEqual(cube_module._RANDOM_CURRENT_GIF, "third.gif")

    @patch("server.display.cube._run_random_cycle")
    @patch("server.display.cube._is_cube_display_on", return_value=True)
    @patch("server.display.cube.time.sleep")
    def test_retries_excluding_failed_gif_and_recovers(
        self, mock_sleep: Mock, mock_on: Mock, mock_cycle: Mock
    ) -> None:
        cube_module._RANDOM_MODE_RUNNING = True
        mock_cycle.side_effect = [(False, "timeout"), (True, "recovered.gif")]

        sleeps = {"count": 0}

        def _stop(_: float) -> None:
            sleeps["count"] += 1
            if sleeps["count"] >= 3:
                cube_module._RANDOM_MODE_RUNNING = False

        mock_sleep.side_effect = _stop

        _random_gif_loop(1, "first.gif")

        self.assertEqual(
            [c.args[0] for c in mock_cycle.call_args_list],
            ["first.gif", "first.gif"],
        )
        self.assertEqual(cube_module._RANDOM_CURRENT_GIF, "recovered.gif")

    @patch("server.display.cube._run_random_cycle")
    @patch("server.display.cube._is_cube_display_on", return_value=False)
    @patch("server.display.cube.time.sleep")
    def test_does_not_cycle_while_display_is_off(
        self, mock_sleep: Mock, mock_on: Mock, mock_cycle: Mock
    ) -> None:
        cube_module._RANDOM_MODE_RUNNING = True

        sleeps = {"count": 0}

        def _stop(_: float) -> None:
            sleeps["count"] += 1
            if sleeps["count"] >= 3:
                cube_module._RANDOM_MODE_RUNNING = False

        mock_sleep.side_effect = _stop

        _random_gif_loop(1, "first.gif")

        mock_cycle.assert_not_called()
        self.assertEqual(cube_module._RANDOM_CURRENT_GIF, None)

    @patch("server.display.cube._run_random_cycle")
    @patch("server.display.cube.time.sleep")
    def test_does_not_cycle_when_stopped_before_first_wait(
        self, mock_sleep: Mock, mock_cycle: Mock
    ) -> None:
        cube_module._RANDOM_MODE_RUNNING = False

        _random_gif_loop(60, "first.gif")

        mock_sleep.assert_not_called()
        mock_cycle.assert_not_called()
        self.assertFalse(cube_module._RANDOM_MODE_RUNNING)


if __name__ == "__main__":
    unittest.main()
