import subprocess
import unittest
from unittest.mock import Mock, patch

from server.audio.micphone import (
    _run_amixer,
    mute_mic,
    unmute_mic,
    set_mic_volume,
    get_mic_mute_state_resource,
    get_mic_volume,
    CAPTURE_CONTROL,
)


def _make_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> Mock:
    result = Mock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _get_real_mic_mute_state() -> bool | None:
    """Query the real system mic mute state via amixer. Returns True if muted, False if unmuted, None if unknown."""
    try:
        result = subprocess.run(
            ["amixer", "get", CAPTURE_CONTROL],
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


def _set_real_mic_mute_state(muted: bool) -> None:
    """Set the real system mic mute state via amixer."""
    action = "nocap" if muted else "cap"
    try:
        subprocess.run(
            ["amixer", "set", CAPTURE_CONTROL, action],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        pass


def _get_real_mic_volume_level() -> int | None:
    """Query the real system mic volume level via amixer. Returns an int 0-100 or None if unknown."""
    try:
        result = subprocess.run(
            ["amixer", "get", CAPTURE_CONTROL],
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


def _set_real_mic_volume_level(level: int) -> None:
    """Set the real system mic volume level via amixer."""
    try:
        subprocess.run(
            ["amixer", "set", CAPTURE_CONTROL, f"{level}%"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        pass


class MuteMicTests(unittest.TestCase):
    def setUp(self) -> None:
        # Capture the real system mic mute state so we can restore it after the test.
        self._original_muted = _get_real_mic_mute_state()

    def tearDown(self) -> None:
        # Restore the original mic mute state if we were able to read it.
        if self._original_muted is not None:
            _set_real_mic_mute_state(self._original_muted)

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result())
    def test_mute_mic_success(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = mute_mic()

        self.assertEqual(result["status"], "muted")
        self.assertEqual(result["message"], "Microphone has been muted.")
        mock_amixer.assert_called_once_with("set", CAPTURE_CONTROL, "nocap")
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_mute_mic_amixer_error(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = mute_mic()

        self.assertEqual(result["status"], "error")
        self.assertIn("Device not found", result["message"])
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", side_effect=RuntimeError("amixer is not installed."))
    def test_mute_mic_missing_amixer(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = mute_mic()

        self.assertEqual(result["status"], "error")
        self.assertIn("amixer is not installed", result["message"])
        mock_run.assert_not_called()


class UnmuteMicTests(unittest.TestCase):
    def setUp(self) -> None:
        # Capture the real system mic mute state so we can restore it after the test.
        self._original_muted = _get_real_mic_mute_state()

    def tearDown(self) -> None:
        # Restore the original mic mute state if we were able to read it.
        if self._original_muted is not None:
            _set_real_mic_mute_state(self._original_muted)

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result())
    def test_unmute_mic_success(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = unmute_mic()

        self.assertEqual(result["status"], "unmuted")
        self.assertEqual(result["message"], "Microphone has been unmuted.")
        mock_amixer.assert_called_once_with("set", CAPTURE_CONTROL, "cap")
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_unmute_mic_amixer_error(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = unmute_mic()

        self.assertEqual(result["status"], "error")
        self.assertIn("Device not found", result["message"])
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", side_effect=RuntimeError("amixer is not installed."))
    def test_unmute_mic_missing_amixer(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = unmute_mic()

        self.assertEqual(result["status"], "error")
        self.assertIn("amixer is not installed", result["message"])
        mock_run.assert_not_called()


class SetMicVolumeTests(unittest.TestCase):
    def setUp(self) -> None:
        # Capture the real system mic volume so we can restore it after the test.
        self._original_level = _get_real_mic_volume_level()

    def tearDown(self) -> None:
        # Restore the original mic volume level if we were able to read it.
        if self._original_level is not None:
            _set_real_mic_volume_level(self._original_level)

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result())
    def test_set_mic_volume_success(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = set_mic_volume(75)

        self.assertEqual(result["status"], "volume-set")
        self.assertEqual(result["level"], 75)
        self.assertIn("75%", result["message"])
        mock_amixer.assert_called_once_with("set", CAPTURE_CONTROL, "75%")
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_set_mic_volume_amixer_error(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = set_mic_volume(50)

        self.assertEqual(result["status"], "error")
        self.assertIn("Device not found", result["message"])
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", side_effect=RuntimeError("amixer is not installed."))
    def test_set_mic_volume_missing_amixer(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = set_mic_volume(50)

        self.assertEqual(result["status"], "error")
        self.assertIn("amixer is not installed", result["message"])
        mock_run.assert_not_called()

    def test_set_mic_volume_below_range(self) -> None:
        result = set_mic_volume(-5)

        self.assertEqual(result["status"], "error")
        self.assertIn("between 0 and 100", result["message"])

    def test_set_mic_volume_above_range(self) -> None:
        result = set_mic_volume(101)

        self.assertEqual(result["status"], "error")
        self.assertIn("between 0 and 100", result["message"])


class GetMicMuteStateResourceTests(unittest.TestCase):
    def setUp(self) -> None:
        # Capture the real system mic mute state so we can restore it after the test.
        self._original_muted = _get_real_mic_mute_state()

    def tearDown(self) -> None:
        # Restore the original mic mute state if we were able to read it.
        if self._original_muted is not None:
            _set_real_mic_mute_state(self._original_muted)

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result(stdout="Capabilities: cvolume cswitch\nCapture: Front Left - Front Right\nLimits: 0 - 100\nFront Left: Capture 40 [40%] [off]\nFront Right: Capture 40 [40%] [off]\n"))
    def test_get_mic_mute_state_muted(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_mic_mute_state_resource()

        self.assertEqual(result, "Microphone is muted.")
        mock_amixer.assert_called_once_with("get", CAPTURE_CONTROL)
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result(stdout="Capabilities: cvolume cswitch\nCapture: Front Left - Front Right\nLimits: 0 - 100\nFront Left: Capture 40 [40%] [on]\nFront Right: Capture 40 [40%] [on]\n"))
    def test_get_mic_mute_state_unmuted(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_mic_mute_state_resource()

        self.assertEqual(result, "Microphone is unmuted.")
        mock_amixer.assert_called_once_with("get", CAPTURE_CONTROL)
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_get_mic_mute_state_amixer_error(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_mic_mute_state_resource()

        self.assertEqual(result, "Could not determine the current microphone mute state.")
        mock_amixer.assert_called_once_with("get", CAPTURE_CONTROL)
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", side_effect=RuntimeError("amixer is not installed."))
    def test_get_mic_mute_state_missing_amixer(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_mic_mute_state_resource()

        self.assertEqual(result, "Could not determine the current microphone mute state.")
        mock_amixer.assert_called_once_with("get", CAPTURE_CONTROL)
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result(stdout="Simple mixer control 'Capture'\n  Capabilities: cvolume cswitch\n  Capture channels: Front Left - Front Right\n  Limits: 0 - 100\n"))
    def test_get_mic_mute_state_unparseable_output(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_mic_mute_state_resource()

        self.assertEqual(result, "Could not determine the current microphone mute state.")


class GetMicVolumeTests(unittest.TestCase):
    def setUp(self) -> None:
        # Capture the real system mic volume so we can restore it after the test.
        self._original_level = _get_real_mic_volume_level()

    def tearDown(self) -> None:
        # Restore the original mic volume level if we were able to read it.
        if self._original_level is not None:
            _set_real_mic_volume_level(self._original_level)

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result(stdout="Simple mixer control 'Capture'\n  Capabilities: cvolume cswitch\n  Capture channels: Front Left - Front Right\n  Limits: 0 - 100\n  Front Left: Capture 40 [40%] [on]\n  Front Right: Capture 40 [40%] [on]\n"))
    @patch("server.audio.micphone._run_amixer", return_value=_make_result(stdout="Front Left: Capture 40 [40%] [on]\nFront Right: Capture 40 [40%] [on]\n"))
    def test_get_mic_volume_success(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_mic_volume()

        self.assertEqual(result, "Current microphone volume: 40%")
        mock_amixer.assert_called_once_with("get", CAPTURE_CONTROL)
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_get_mic_volume_amixer_error(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_mic_volume()

        self.assertEqual(result, "Could not determine the current microphone volume level.")
        mock_amixer.assert_called_once_with("get", CAPTURE_CONTROL)
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", side_effect=RuntimeError("amixer is not installed."))
    def test_get_mic_volume_missing_amixer(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_mic_volume()

        self.assertEqual(result, "Could not determine the current microphone volume level.")
        mock_amixer.assert_called_once_with("get", CAPTURE_CONTROL)
        mock_run.assert_not_called()

    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    @patch("server.audio.micphone._run_amixer", return_value=_make_result(stdout="Simple mixer control 'Capture'\n  Capabilities: cvolume cswitch\n"))
    def test_get_mic_volume_unparseable_output(self, mock_amixer: Mock, mock_run: Mock) -> None:
        result = get_mic_volume()

        self.assertEqual(result, "Could not determine the current microphone volume level.")


class MicRunAmixerTests(unittest.TestCase):
    @patch("server.audio.micphone.shutil.which", return_value="/usr/bin/amixer")
    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    def test_run_amixer_uses_amixer_path(self, mock_run: Mock, mock_which: Mock) -> None:
        _run_amixer("set", "Capture", "nocap")

        mock_run.assert_called_once_with(
            ["/usr/bin/amixer", "set", "Capture", "nocap"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("server.audio.micphone.shutil.which", return_value=None)
    @patch("server.audio.micphone.subprocess.run", return_value=_make_result())
    def test_run_amixer_raises_when_not_installed(self, mock_run: Mock, mock_which: Mock) -> None:
        with self.assertRaises(RuntimeError):
            _run_amixer("set", "Capture", "nocap")
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()