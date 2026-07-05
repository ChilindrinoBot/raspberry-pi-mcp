import base64
import unittest
from unittest.mock import Mock, patch

from server.audio.play import _build_player_command, _decode_audio_payload, stop_audio


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
    def test_returns_idle_when_nothing_is_playing(self) -> None:
        with patch("server.audio.play._ACTIVE_PLAYER_PROCESS", None):
            self.assertEqual(stop_audio(), {"status": "stopped", "message": "There is no active audio to stop."})

    def test_terminates_active_process(self) -> None:
        process = Mock()
        process.poll.return_value = None

        with patch("server.audio.play._is_ffplay_running", return_value=True), \
             patch("server.audio.play._ACTIVE_PLAYER_PROCESS", process):
            result = stop_audio()

        self.assertEqual(result["status"], "stopped")
        process.terminate.assert_called_once_with()


class PlayerCommandTests(unittest.TestCase):
    def test_build_player_command_uses_file_path_for_ffplay(self) -> None:
        with patch("server.audio.play.shutil.which", side_effect=lambda name: "/usr/bin/ffplay" if name == "ffplay" else None):
            command = _build_player_command()

        self.assertEqual(command[0], "/usr/bin/ffplay")
        self.assertIn("-nodisp", command)
        self.assertIn("-autoexit", command)
        self.assertIn("-", command)


if __name__ == "__main__":
    unittest.main()
