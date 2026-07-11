import unittest
from unittest.mock import patch

from server.audio.notify import list_notification_audios


class NotificationAudioTests(unittest.TestCase):
    def test_list_notification_audios_returns_list(self) -> None:
        # Test that it returns a string containing expected keywords
        result = list_notification_audios()
        self.assertIsInstance(result, str)
        self.assertIn("Available notification sounds:", result)

    def test_list_notification_audios_empty(self) -> None:
        with patch("server.audio.notify.Path.exists", return_value=False), \
             patch("server.audio.notify.Path.is_dir", return_value=False):
            result = list_notification_audios()
            self.assertEqual(result, "No notification audio files found.")


if __name__ == "__main__":
    unittest.main()
