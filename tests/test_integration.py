import unittest
import base64
import time
from server.audio.play import play_audio, stop_audio
from server.audio.notify import notify_audio

class AudioIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure audio is stopped before each test
        stop_audio()

    def tearDown(self) -> None:
        # Ensure audio is stopped after each test to avoid noise
        stop_audio()

    def test_play_and_stop_cycle(self) -> None:
        # We'll use the actual audio.mp3 if it exists, but just for a split second.
        try:
            with open("audio.mp3", "rb") as f:
                encoded_audio = base64.b64encode(f.read()).decode("ascii")
        except FileNotFoundError:
            encoded_audio = base64.b64encode(b"dummy audio data").decode("ascii")

        # 1. Test starting playback
        result = play_audio(encoded_audio)
        self.assertEqual(result["status"], "playing")
        
        # 2. Wait for a short duration (well under 3 seconds)
        time.sleep(1)
        
        # 3. Test stopping playback
        stop_result = stop_audio()
        self.assertEqual(stop_result["status"], "stopped")

    def test_busy_status(self) -> None:
        try:
            with open("audio.mp3", "rb") as f:
                encoded_audio = base64.b64encode(f.read()).decode("ascii")
        except FileNotFoundError:
            encoded_audio = base64.b64encode(b"dummy audio data").decode("ascii")

        # Start first playback
        play_audio(encoded_audio)
        
        # Attempt to start another immediately
        result = play_audio(encoded_audio)
        self.assertEqual(result["status"], "busy")

    def test_notify_audio_default(self) -> None:
        # Test playing the default notification sound
        result = notify_audio(random_sound=False)
        self.assertEqual(result["status"], "success")
        time.sleep(1)

    def test_notify_audio_random(self) -> None:
        # Test playing a random notification sound
        result = notify_audio(random_sound=True)
        self.assertEqual(result["status"], "success")
        time.sleep(1)

if __name__ == "__main__":
    unittest.main()

