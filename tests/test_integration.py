import unittest
import base64
from unittest.mock import Mock, patch

from server.audio.manager import audio_manager
from server.audio.play import play_audio, stop_audio, play_audio_file
from server.audio.notify import notify_audio


def _make_process_mock(pid: int = 12345) -> Mock:
    """Creates a fake Popen-like process that pretends to be alive."""
    process = Mock()
    process.pid = pid
    process.poll.return_value = None  # alive while the test runs
    process.stdin = Mock()
    process.terminate.return_value = None
    process.kill.return_value = None
    process.wait.return_value = 0
    return process


class AudioIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        # Clear any state left behind by the global AudioManager singleton.
        audio_manager._started_pids.clear()
        audio_manager._processes.clear()

    def tearDown(self) -> None:
        audio_manager._started_pids.clear()
        audio_manager._processes.clear()

    @patch("server.audio.manager.os.kill")
    @patch("server.audio.play.shutil.which", return_value="/usr/bin/ffplay")
    @patch("server.audio.play.subprocess.Popen", return_value=_make_process_mock())
    @patch("server.audio.manager.subprocess.Popen", return_value=_make_process_mock())
    def test_play_and_stop_cycle(
        self,
        mock_manager_popen: Mock,
        mock_play_popen: Mock,
        mock_which: Mock,
        mock_kill: Mock,
    ) -> None:
        encoded_audio = base64.b64encode(b"dummy audio data").decode("ascii")

        result = play_audio(encoded_audio)
        self.assertEqual(result["status"], "playing")

        stop_result = stop_audio()
        self.assertEqual(stop_result["status"], "stopped")

        # Ensure a real ffplay process was never spawned.
        mock_play_popen.assert_called_once()

    @patch("server.audio.manager.os.kill")
    @patch("server.audio.play.shutil.which", return_value="/usr/bin/ffplay")
    @patch("server.audio.play.subprocess.Popen", return_value=_make_process_mock())
    @patch("server.audio.manager.subprocess.Popen", return_value=_make_process_mock())
    def test_busy_status(
        self,
        mock_manager_popen: Mock,
        mock_play_popen: Mock,
        mock_which: Mock,
        mock_kill: Mock,
    ) -> None:
        encoded_audio = base64.b64encode(b"dummy audio data").decode("ascii")

        first = play_audio(encoded_audio)
        self.assertEqual(first["status"], "playing")

        second = play_audio(encoded_audio)
        self.assertEqual(second["status"], "busy")

    @patch("server.audio.manager.subprocess.Popen", return_value=_make_process_mock())
    def test_notify_audio_default(self, mock_manager_popen: Mock) -> None:
        result = notify_audio(random_sound=False)
        self.assertEqual(result["status"], "success")
        mock_manager_popen.assert_called_once()

    @patch("server.audio.manager.subprocess.Popen", return_value=_make_process_mock())
    def test_notify_audio_random(self, mock_manager_popen: Mock) -> None:
        result = notify_audio(random_sound=True)
        self.assertEqual(result["status"], "success")
        mock_manager_popen.assert_called_once()

    @patch("server.audio.play.Path.exists", return_value=True)
    @patch("server.audio.manager.os.kill")
    @patch("server.audio.manager.subprocess.Popen", return_value=_make_process_mock())
    def test_play_audio_file_success(
        self,
        mock_manager_popen: Mock,
        mock_kill: Mock,
        mock_path_exists: Mock,
    ) -> None:
        result = play_audio_file("/tmp/fake_audio.mp3")
        self.assertEqual(result["status"], "playing")
        mock_manager_popen.assert_called_once()

    def test_play_audio_file_not_found(self) -> None:
        result = play_audio_file("/tmp/non_existent_audio.mp3")
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["message"])

    @patch("server.audio.play.Path.exists", return_value=True)
    @patch("server.audio.manager.os.kill")
    @patch("server.audio.manager.subprocess.Popen", return_value=_make_process_mock())
    def test_play_audio_file_busy(
        self,
        mock_manager_popen: Mock,
        mock_kill: Mock,
        mock_path_exists: Mock,
    ) -> None:
        first = play_audio_file("/tmp/fake_audio.mp3")
        self.assertEqual(first["status"], "playing")

        second = play_audio_file("/tmp/fake_audio.mp3")
        self.assertEqual(second["status"], "busy")


if __name__ == "__main__":
    unittest.main()