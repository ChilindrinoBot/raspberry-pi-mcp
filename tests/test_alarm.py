import unittest
from unittest.mock import patch
from pathlib import Path

from server.audio.alarm import list_alarm_audios


class ListAlarmAudiosTests(unittest.TestCase):
    def test_returns_alarm_list_when_files_exist(self) -> None:
        fake_alarms = [
            Path("/fake/alarms/alarm1.mp3"),
            Path("/fake/alarms/alarm2.mp3"),
        ]
        with patch("server.audio.alarm.ALARMS_DIR") as mock_dir:
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_dir.glob.return_value = fake_alarms

            result = list_alarm_audios()

        self.assertIn("Available alarms:", result)
        self.assertIn("alarm1.mp3", result)
        self.assertIn("alarm2.mp3", result)

    def test_returns_no_directory_when_dir_missing(self) -> None:
        with patch("server.audio.alarm.ALARMS_DIR") as mock_dir:
            mock_dir.exists.return_value = False

            result = list_alarm_audios()

        self.assertEqual(result, "No alarms directory found.")

    def test_returns_no_files_when_dir_empty(self) -> None:
        with patch("server.audio.alarm.ALARMS_DIR") as mock_dir:
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_dir.glob.return_value = []

            result = list_alarm_audios()

        self.assertEqual(result, "No alarm audio files found.")

    def test_returns_no_directory_when_path_is_file(self) -> None:
        with patch("server.audio.alarm.ALARMS_DIR") as mock_dir:
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = False

            result = list_alarm_audios()

        self.assertEqual(result, "No alarms directory found.")


if __name__ == "__main__":
    unittest.main()
