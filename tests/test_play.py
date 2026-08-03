import base64
import unittest
from unittest.mock import Mock, patch, MagicMock

from server.audio.play import _build_player_command, _decode_audio_payload, stop_audio, _STARTED_PIDS


class DecodeAudioPayloadTests(unittest.TestCase):
    def test_decodes_valid_base64_payload(self) -> None:
        payload = b"audio-bytes"
        encoded = base64.b64encode(payload).decode("ascii")

        self.assertEqual(_decode_audio_payload(encoded, max_bytes=1024), payload)

    def test_rejects_invalid_base64_payload(self) -> None:
        with self.assertRaises(ValueError):
            _decode_audio_payload("not-valid-base64")

    def test_rejects_payload_above_limit(self) -> None:
        encoded = base64.b64encode(b"x" * 16).decode("ascii")

        with self.assertRaises(ValueError):
            _decode_audio_payload(encoded, max_bytes=8)


class StopAudioTests(unittest.TestCase):
    def setUp(self) -> None:
        _STARTED_PIDS.clear()

    def tearDown(self) -> None:
        _STARTED_PIDS.clear()

    def test_returns_idle_when_nothing_is_playing(self) -> None:
        # No PIDs registered → nothing is playing
        result = stop_audio()
        self.assertEqual(result, {"status": "stopped", "message": "There is no active audio to stop."})

    def test_terminates_tracked_pid(self) -> None:
        """stop_audio must send SIGTERM only to PIDs registered by this server."""
        import signal as signal_module
        _STARTED_PIDS.add(99999)

        with patch("server.audio.play.os.kill") as mock_kill:
            # Simulate: os.kill(pid, 0) succeeds (process alive), os.kill(pid, SIGTERM) succeeds
            mock_kill.side_effect = lambda pid, sig: None
            result = stop_audio()

        self.assertEqual(result["status"], "stopped")
        # Verify SIGTERM was sent to our specific PID, not a global pkill
        mock_kill.assert_any_call(99999, signal_module.SIGTERM)

    def test_does_not_call_pkill(self) -> None:
        """stop_audio must never call pkill — it must not affect unrelated processes."""
        _STARTED_PIDS.add(99999)

        with patch("server.audio.play.os.kill"), \
             patch("server.audio.play.subprocess.run") as mock_run:
            stop_audio()

        mock_run.assert_not_called()

    def test_cleans_up_dead_pids_on_check(self) -> None:
        """_is_ffplay_running must remove stale PIDs whose process no longer exists."""
        from server.audio.play import _is_ffplay_running
        _STARTED_PIDS.add(99998)

        with patch("server.audio.play.os.kill", side_effect=ProcessLookupError):
            running = _is_ffplay_running()

        self.assertFalse(running)
        self.assertNotIn(99998, _STARTED_PIDS)


class PlayerCommandTests(unittest.TestCase):
    def test_build_player_command_uses_ffplay(self) -> None:
        with patch("server.audio.play.shutil.which", side_effect=lambda name: "/usr/bin/ffplay" if name == "ffplay" else None):
            command = _build_player_command()

        self.assertEqual(command[0], "/usr/bin/ffplay")
        self.assertIn("-nodisp", command)
        self.assertIn("-autoexit", command)
        self.assertIn("-", command)

    def test_raises_when_ffplay_not_installed(self) -> None:
        with patch("server.audio.play.shutil.which", return_value=None):
            with self.assertRaises(RuntimeError):
                _build_player_command()


if __name__ == "__main__":
    unittest.main()
