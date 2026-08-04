import subprocess
import unittest
from unittest.mock import Mock, patch

from server.audio.speaker import _run_amixer, mute, unmute, MASTER_CONTROL


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