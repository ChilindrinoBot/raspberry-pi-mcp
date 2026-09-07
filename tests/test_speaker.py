import subprocess
import unittest
from unittest.mock import Mock, patch

from server.audio.speaker import _run_pactl, _get_default_sink, mute, unmute, set_volume, get_volume

FAKE_SINK = "alsa_output.usb-TestDevice-00.iec958-stereo"


def _make_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> Mock:
    result = Mock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _get_real_sink() -> str | None:
    """Get the real default sink from the system."""
    try:
        result = subprocess.run(
            ["pactl", "get-default-sink"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, OSError):
        pass
    return None


def _get_real_mute_state() -> bool | None:
    """Query the real system mute state via pactl."""
    sink = _get_real_sink()
    if not sink:
        return None
    try:
        result = subprocess.run(
            ["pactl", "get-sink-mute", sink],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None

    if result.returncode != 0:
        return None

    if "yes" in result.stdout.lower():
        return True
    if "no" in result.stdout.lower():
        return False
    return None


def _set_real_mute_state(muted: bool) -> None:
    """Set the real system mute state via pactl."""
    sink = _get_real_sink()
    if not sink:
        return
    value = "1" if muted else "0"
    try:
        subprocess.run(
            ["pactl", "set-sink-mute", sink, value],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        pass


def _get_real_volume_level() -> int | None:
    """Query the real system volume level via pactl."""
    sink = _get_real_sink()
    if not sink:
        return None
    try:
        result = subprocess.run(
            ["pactl", "get-sink-volume", sink],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None

    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        if "%" in line:
            try:
                idx = line.index("%")
                start = line.rfind(" ", 0, idx) + 1
                return int(line[start:idx])
            except ValueError:
                continue
    return None


def _set_real_volume_level(level: int) -> None:
    """Set the real system volume level via pactl."""
    sink = _get_real_sink()
    if not sink:
        return
    try:
        subprocess.run(
            ["pactl", "set-sink-volume", sink, f"{level}%"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        pass


class GetDefaultSinkTests(unittest.TestCase):
    @patch("server.audio.speaker._run_pactl", return_value=_make_result(stdout="alsa_output.usb-TestDevice-00.iec958-stereo\n"))
    def test_get_default_sink_success(self, mock_pactl: Mock) -> None:
        result = _get_default_sink()
        self.assertEqual(result, "alsa_output.usb-TestDevice-00.iec958-stereo")
        mock_pactl.assert_called_once_with("get-default-sink")

    @patch("server.audio.speaker._run_pactl", return_value=_make_result(returncode=1, stderr="No sink found"))
    def test_get_default_sink_no_sink(self, mock_pactl: Mock) -> None:
        with self.assertRaises(RuntimeError):
            _get_default_sink()

    @patch("server.audio.speaker._run_pactl", return_value=_make_result(stdout="\n"))
    def test_get_default_sink_empty_output(self, mock_pactl: Mock) -> None:
        with self.assertRaises(RuntimeError):
            _get_default_sink()


class MuteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_muted = _get_real_mute_state()

    def tearDown(self) -> None:
        if self._original_muted is not None:
            _set_real_mute_state(self._original_muted)

    @patch("server.audio.speaker._get_default_sink", return_value=FAKE_SINK)
    @patch("server.audio.speaker._run_pactl", return_value=_make_result())
    def test_mute_success(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = mute()

        self.assertEqual(result["status"], "muted")
        self.assertEqual(result["message"], "Audio output has been muted.")
        mock_sink.assert_called_once()
        mock_pactl.assert_called_once_with("set-sink-mute", FAKE_SINK, "1")

    @patch("server.audio.speaker._get_default_sink", return_value=FAKE_SINK)
    @patch("server.audio.speaker._run_pactl", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_mute_pactl_error(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = mute()

        self.assertEqual(result["status"], "error")
        self.assertIn("Device not found", result["message"])

    @patch("server.audio.speaker._get_default_sink", side_effect=RuntimeError("No default audio sink found."))
    @patch("server.audio.speaker._run_pactl", return_value=_make_result())
    def test_mute_no_sink(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = mute()

        self.assertEqual(result["status"], "error")
        self.assertIn("No default audio sink found", result["message"])
        mock_pactl.assert_not_called()

    @patch("server.audio.speaker._get_default_sink", return_value=FAKE_SINK)
    @patch("server.audio.speaker._run_pactl", side_effect=RuntimeError("pactl is not installed."))
    def test_mute_missing_pactl(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = mute()

        self.assertEqual(result["status"], "error")
        self.assertIn("pactl is not installed", result["message"])


class UnmuteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_muted = _get_real_mute_state()

    def tearDown(self) -> None:
        if self._original_muted is not None:
            _set_real_mute_state(self._original_muted)

    @patch("server.audio.speaker._get_default_sink", return_value=FAKE_SINK)
    @patch("server.audio.speaker._run_pactl", return_value=_make_result())
    def test_unmute_success(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = unmute()

        self.assertEqual(result["status"], "unmuted")
        self.assertEqual(result["message"], "Audio output has been unmuted.")
        mock_sink.assert_called_once()
        mock_pactl.assert_called_once_with("set-sink-mute", FAKE_SINK, "0")

    @patch("server.audio.speaker._get_default_sink", return_value=FAKE_SINK)
    @patch("server.audio.speaker._run_pactl", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_unmute_pactl_error(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = unmute()

        self.assertEqual(result["status"], "error")
        self.assertIn("Device not found", result["message"])

    @patch("server.audio.speaker._get_default_sink", side_effect=RuntimeError("No default audio sink found."))
    @patch("server.audio.speaker._run_pactl", return_value=_make_result())
    def test_unmute_no_sink(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = unmute()

        self.assertEqual(result["status"], "error")
        self.assertIn("No default audio sink found", result["message"])
        mock_pactl.assert_not_called()


class SetVolumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_level = _get_real_volume_level()

    def tearDown(self) -> None:
        if self._original_level is not None:
            _set_real_volume_level(self._original_level)

    @patch("server.audio.speaker._get_default_sink", return_value=FAKE_SINK)
    @patch("server.audio.speaker._run_pactl", return_value=_make_result())
    def test_set_volume_success(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = set_volume(75)

        self.assertEqual(result["status"], "volume-set")
        self.assertEqual(result["level"], 75)
        self.assertIn("75%", result["message"])
        mock_sink.assert_called_once()
        mock_pactl.assert_called_once_with("set-sink-volume", FAKE_SINK, "75%")

    @patch("server.audio.speaker._get_default_sink", return_value=FAKE_SINK)
    @patch("server.audio.speaker._run_pactl", return_value=_make_result(returncode=1, stderr="Device not found"))
    def test_set_volume_pactl_error(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = set_volume(50)

        self.assertEqual(result["status"], "error")
        self.assertIn("Device not found", result["message"])

    @patch("server.audio.speaker._get_default_sink", side_effect=RuntimeError("No default audio sink found."))
    @patch("server.audio.speaker._run_pactl", return_value=_make_result())
    def test_set_volume_no_sink(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = set_volume(50)

        self.assertEqual(result["status"], "error")
        self.assertIn("No default audio sink found", result["message"])
        mock_pactl.assert_not_called()

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
        self._original_level = _get_real_volume_level()

    def tearDown(self) -> None:
        if self._original_level is not None:
            _set_real_volume_level(self._original_level)

    @patch("server.audio.speaker._get_default_sink", return_value=FAKE_SINK)
    @patch("server.audio.speaker._run_pactl", return_value=_make_result(stdout="Volume: front-left: 47191 / 72% / -8.06 dB, front-right: 47191 / 72% / -8.06 dB"))
    def test_get_volume_success(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = get_volume()

        self.assertEqual(result, "Current volume: 72%")
        mock_sink.assert_called_once()
        mock_pactl.assert_called_once_with("get-sink-volume", FAKE_SINK)

    @patch("server.audio.speaker._get_default_sink", return_value=FAKE_SINK)
    @patch("server.audio.speaker._run_pactl", return_value=_make_result(returncode=1, stderr="No such sink"))
    def test_get_volume_pactl_error(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = get_volume()

        self.assertEqual(result, "Could not determine the current volume level.")

    @patch("server.audio.speaker._get_default_sink", side_effect=RuntimeError("No default audio sink found."))
    @patch("server.audio.speaker._run_pactl", return_value=_make_result())
    def test_get_volume_no_sink(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = get_volume()

        self.assertEqual(result, "Could not determine the current volume level.")
        mock_pactl.assert_not_called()

    @patch("server.audio.speaker._get_default_sink", return_value=FAKE_SINK)
    @patch("server.audio.speaker._run_pactl", return_value=_make_result(stdout="No volume info available"))
    def test_get_volume_unparseable_output(self, mock_pactl: Mock, mock_sink: Mock) -> None:
        result = get_volume()

        self.assertEqual(result, "Could not determine the current volume level.")


class RunPactlTests(unittest.TestCase):
    @patch("server.audio.speaker.shutil.which", return_value="/usr/bin/pactl")
    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    def test_run_pactl_uses_pactl_path(self, mock_run: Mock, mock_which: Mock) -> None:
        _run_pactl("set-sink-mute", "test-sink", "1")

        mock_run.assert_called_once_with(
            ["/usr/bin/pactl", "set-sink-mute", "test-sink", "1"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("server.audio.speaker.shutil.which", return_value=None)
    @patch("server.audio.speaker.subprocess.run", return_value=_make_result())
    def test_run_pactl_raises_when_not_installed(self, mock_run: Mock, mock_which: Mock) -> None:
        with self.assertRaises(RuntimeError):
            _run_pactl("set-sink-mute", "test-sink", "1")
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
