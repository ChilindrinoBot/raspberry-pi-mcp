import unittest
import base64
import time
from server.audio.play import play_audio, stop_audio

class AudioIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure audio is stopped before each test
        stop_audio()

    def tearDown(self) -> None:
        # Ensure audio is stopped after each test to avoid noise
        stop_audio()

    def test_play_and_stop_cycle(self) -> None:
        # Use a tiny dummy base64 audio payload (minimal valid audio data)
        # For a real integration test, we could load a small file, but a tiny 
        # payload is safer for ruido.
        # Let's use a very small real audio if possible, or just a small base64 string.
        # Since play_audio expects valid base64 and ffplay handles the bytes,
        # we use a small valid audio snippet.
        
        # We'll use the actual audio.mp3 if it exists, but just for a split second.
        try:
            with open("audio.mp3", "rb") as f:
                encoded_audio = base64.b64encode(f.read()).decode("ascii")
        except FileNotFoundError:
            # Fallback to a dummy payload if file is missing
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

if __name__ == "__main__":
    unittest.main()
