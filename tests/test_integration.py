import unittest
import base64
import time
from server.audio.play import play_audio, stop_audio, play_audio_file
from server.audio.notify import notify_audio

class AudioIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure audio is stopped before each test
        stop_audio()

    def tearDown(self) -> None:
        # Ensure audio is stopped after each test to avoid noise
        stop_audio()

    def test_play_and_stop_cycle(self) -> None:
        try:
            with open("tests/media/audio.mp3", "rb") as f:
                encoded_audio = base64.b64encode(f.read()).decode("ascii")
        except FileNotFoundError:
            encoded_audio = base64.b64encode(b"dummy audio data").decode("ascii")

        result = play_audio(encoded_audio)
        self.assertEqual(result["status"], "playing")
        time.sleep(1)
        stop_result = stop_audio()
        self.assertEqual(stop_result["status"], "stopped")

    def test_busy_status(self) -> None:
        try:
            with open("tests/media/audio.mp3", "rb") as f:
                encoded_audio = base64.b64encode(f.read()).decode("ascii")
        except FileNotFoundError:
            encoded_audio = base64.b64encode(b"dummy audio data").decode("ascii")

        play_audio(encoded_audio)
        result = play_audio(encoded_audio)
        self.assertEqual(result["status"], "busy")

    def test_notify_audio_default(self) -> None:
        result = notify_audio(random_sound=False)
        self.assertEqual(result["status"], "success")
        time.sleep(1)

    def test_notify_audio_random(self) -> None:
        result = notify_audio(random_sound=True)
        self.assertEqual(result["status"], "success")
        time.sleep(1)

    def test_play_audio_file_success(self) -> None:
        file_path = "tests/media/audio.mp3"
        result = play_audio_file(file_path)
        self.assertEqual(result["status"], "playing")
        time.sleep(1)

    def test_play_audio_file_not_found(self) -> None:
        result = play_audio_file("/tmp/non_existent_audio.mp3")
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["message"])

    def test_play_audio_file_busy(self) -> None:
        file_path = "tests/media/audio.mp3"
        play_audio_file(file_path)
        result = play_audio_file(file_path)
        self.assertEqual(result["status"], "busy")
        time.sleep(1)

if __name__ == "__main__":
    unittest.main()
