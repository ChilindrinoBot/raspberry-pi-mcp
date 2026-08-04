import subprocess
import unittest
from unittest.mock import Mock, patch

from server.audio.speaker import _run_amixer, mute, unmute, set_volume, get_volume, MASTER_CONTROL


def _make_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> Mock:
    result = Mock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _get_real_mute_state() -> bool | None:
    """Query the real system mute state via amixer. Returns True if muted, False if unmuted, None if unknown."""
    try:
        result = subprocess.run(
            ["amixer", "get", MASTER_CONTROL],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None

    if result.returncode != 0:
        return None

    # amixer output contains "[on]" or "[off]" for the mute state.
    if "[off]" in result.stdout:
        return True
    if "[on]" in result.stdout:
        return False
    return None


def _set_real_mute_state(muted: bool) -> None:
    """Set the real system mute state via amixer."""
    action = "mute" if muted else "unmute"
    try:
        subprocess.run(
            ["amixer", "set", MASTER_CONTROL, action],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        pass


def _get_real_volume_level() -> int | None:
    """Query the real system volume level via amixer. Returns an int 0-100 or None if unknown."""
    try:
        result = subprocess.run(
            ["amixer", "get", MASTER_CONTROL],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None

    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        if "[" in line and "%]" in line:
            try:
                start = line.index("[") + 1
                end = line.index("%]")
                return int(line[start:end])
            except ValueError:
                continue
    return None


def _set_real_volume_level(level: int) -> None:
    """Set the real system volume level via amixer."""
    try:
        subprocess.run(
            ["amixer", "set", MASTER_CONTROL, f"{level}%"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        pass


class MuteTests(unittest.TestCase):
    def setUp(self) -> None:
        # Capture the real system mute state so we can restore it after the test.
        self._original_muted = _get_real_mute_state()

    def tearDown(self) -> None:
        # Restore the original mute state if we were able to read it.
        if self._original_muted is not None:
            _set_real_mute_state(self._original_muted)

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", return_value=_make_result())
    def test_mute_success(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = mute()

        self.assertEqual(result["status"], "muted")
        self.assertEqual(result["message"], "Audio output has been muted.")
        mock_amixer.assert_called_once_with("set", MASTER_CONTROL, "mute")
        mock_run.assert_not_called()

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_mute_amixer_error(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = mute()

        self.assertEqual(result["status"], "error")
        self.assertIn("Device not found", result["message"])
        mock_run.assert_not_called()

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", side_effect=RuntimeError("amixer is not installed."))
    def test_mute_missing_amixer(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = mute()

        self.assertEqual(result["status"], "error")
        self.assertIn("amixer is not installed", result["message"])
        mock_run.assert_not_called()


class UnmuteTests(unittest.TestCase):
    def setUp(self) -> None:
        # Capture the real system mute state so we can restore it after the test.
        self._original_muted = _get_real_mute_state()

    def tearDown(self) -> None:
        # Restore the original mute state if we were able to read it.
        if self._original_muted is not None:
            _set_real_mute_state(self._original_muted)

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", return_value=_make_result())
    def test_unmute_success(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = unmute()

        self.assertEqual(result["status"], "unmuted")
        self.assertEqual(result["message"], "Audio output has been unmuted.")
        mock_amixer.assert_called_once_with("set", MASTER_CONTROL, "unmute")
        mock_run.assert_not_called()

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_unmute_amixer_error(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = unmute()

        self.assertEqual(result["status"], "error")
        self.assertIn("Device not found", result["message"])
        mock_run.assert_not_called()

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", side_effect=RuntimeError("amixer is not installed."))
    def test_unmute_missing_amixer(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = unmute()

        self.assertEqual(result["status"], "error")
        self.assertIn("amixer is not installed", result["message"])
        mock_run.assert_not_called()


class SetVolumeTests(unittest.TestCase):
    def setUp(self) -> None:
        # Capture the real system volume so we can restore it after the test.
        self._original_level = _get_real_volume_level()

    def tearDown(self) -> None:
        # Restore the original volume level if we were able to read it.
        if self._original_level is not None:
            _set_real_volume_level(self._original_level)

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", return_value=_make_result())
    def test_set_volume_success(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = set_volume(75)

        self.assertEqual(result["status"], "volume-set")
        self.assertEqual(result["level"], 75)
        self.assertIn("75%", result["message"])
        mock_amixer.assert_called_once_with("set", MASTER_CONTROL, "75%")
        mock_run.assert_not_called()

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_set_volume_amixer_error(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = set_volume(50)

        self.assertEqual(result["status"], "error")
        self.assertIn("Device not found", result["message"])
        mock_run.assert_not_called()

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", side_effect=RuntimeError("amixer is not installed."))
    def test_set_volume_missing_amixer(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = set_volume(50)

        self.assertEqual(result["status"], "error")
        self.assertIn("amixer is not installed", result["message"])
        mock_run.assert_not_called()

    def test_set_volume_below_range(self) -> None:
        result = set_volume(-5)

        self.assertEqual(result["status"], "error")
        self.assertIn("between 0 and 100", result["message"])

    def test_set_volume_above_range(self) -> None:
        result = set_volume(101)

        self.assertEqual(result["status"], "error")
        self.assertIn("between 0 and 100", result["message"])


class GetVolumeTests(unittest.TestCase):
    def setUp(self) -> None:
        # Capture the real system volume so we can restore it after the test.
        self._original_level = _get_real_volume_level()

    def tearDown(self) -> None:
        # Restore the original volume level if we were able to read it.
        if self._original_level is not None:
            _set_real_volume_level(self._original_level)

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result(stdout="Simple mixer control 'Master'\n  Capabilities: pvolume pswitch\n  Playback channels: Front Left - Front Right\n  Limits: 0 - 100\n  Mono:\n  Front Left: Playback 40 [40%] [on]\n  Front Right: Playback 40 [40%] [on]\n"))
    @patch("server.audio.speaker._run_amixer", return_value=_make_result(stdout="Front Left: Playback 40 [40%] [on]\nFront Right: Playback 40 [40%] [on]\n"))
    def test_get_volume_success(self, mock_amixer: Mock, mock_run: Mock) -> None:
        # The real amixer call is via _get_volume_level -> _run_amixer.
        # Patch _run_amixer for the internal call and subprocess.run for safety.
        result = get_volume()

        self.assertEqual(result, "Current volume: 40%")
        mock_amixer.assert_called_once_with("get", MASTER_CONTROL)
        mock_run.assert_not_called()

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_get_volume_amixer_error(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_volume()

        self.assertEqual(result, "Could not determine the current volume level.")
        mock_amixer.assert_called_once_with("get", MASTER_CONTROL)
        mock_run.assert_not_called()

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", side_effect=RuntimeError("amixer is not installed."))
    def test_get_volume_missing_amixer(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_volume()

        self.assertEqual(result, "Could not determine the current volume level.")
        mock_amixer.assert_called_once_with("get", MASTER_CONTROL)
        mock_run.assert_not_called()

    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    @patch("server.audio.speaker._run_amixer", return_value=_make_result(stdout="Simple mixer control 'Master'\n  Capabilities: pvolume pswitch\n"))
    def test_get_volume_unparseable_output(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_volume()

        self.assertEqual(result, "Could not determine the current volume level.")


class RunAmixerTests(unittest.TestCase):
    @patch("server.audio.speaker.shutil.which", return_value="/usr/bin/amixer")
    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    def test_run_amixer_uses_amixer_path(self, mock_run: Mock, mock_which: Mock) -> None:
        _run_amixer("set", "Master", "mute")

        mock_run.assert_called_once_with(
            ["/usr/bin/amixer", "set", "Master", "mute"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("server.audio.speaker.shutil.which", return_value=None)
    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    def test_run_amixer_raises_when_not_installed(self, mock_run: Mock, mock_which: Mock) -> None:
        with self.assertRaises(RuntimeError):
            _run_amixer("set", "Master", "mute")
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()