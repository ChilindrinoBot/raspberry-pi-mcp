import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from server.audio.alarm import list_alarm_audios, play_alarm, DEFAULT_ALARM_STOP_TIME


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


class PlayAlarmTests(unittest.TestCase):
    @patch("server.audio.alarm.threading.Timer")
    @patch("server.audio.alarm._is_ffplay_running", return_value=False)
    @patch("server.audio.alarm.subprocess.Popen")
    @patch("server.audio.alarm.MEDIA_ROOT")
    def test_plays_default_alarm_and_schedules_stop(
        self, mock_media_root, mock_popen, mock_ffplay, mock_timer
    ) -> None:
        mock_alarm_path = mock_media_root / "default" / "alarm.mp3"
        mock_alarm_path.exists.return_value = True
        mock_popen.return_value.pid = 12345

        mock_timer_inst = MagicMock()
        mock_timer.return_value = mock_timer_inst

        result = play_alarm()

        self.assertEqual(result["status"], "playing")
        mock_popen.assert_called_once()
        mock_timer_inst.start.assert_called_once()

    @patch("server.audio.alarm._is_ffplay_running", return_value=True)
    def test_returns_busy_when_audio_playing(self, mock_ffplay) -> None:
        result = play_alarm()
        self.assertEqual(result["status"], "busy")

    @patch("server.audio.alarm._is_ffplay_running", return_value=False)
    @patch("server.audio.alarm.MEDIA_ROOT")
    def test_returns_error_when_alarm_not_found(self, mock_media_root, mock_ffplay) -> None:
        mock_alarm_path = mock_media_root / "default" / "alarm.mp3"
        mock_alarm_path.exists.return_value = False

        result = play_alarm()

        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["message"])

    @patch("server.audio.alarm.threading.Timer")
    @patch("server.audio.alarm._is_ffplay_running", return_value=False)
    @patch("server.audio.alarm.subprocess.Popen")
    @patch("server.audio.alarm.MEDIA_ROOT")
    def test_uses_custom_stop_time(
        self, mock_media_root, mock_popen, mock_ffplay, mock_timer
    ) -> None:
        mock_alarm_path = mock_media_root / "default" / "alarm.mp3"
        mock_alarm_path.exists.return_value = True
        mock_popen.return_value.pid = 12345

        mock_timer_inst = MagicMock()
        mock_timer.return_value = mock_timer_inst

        result = play_alarm(stop_time=120)

        self.assertEqual(result["status"], "playing")
        self.assertIn("120s", result["message"])
        # Timer must be created with the custom stop time
        mock_timer.assert_called_once_with(120, unittest.mock.ANY)

    @patch("server.audio.alarm.threading.Timer")
    @patch("server.audio.alarm._is_ffplay_running", return_value=False)
    @patch("server.audio.alarm.ALARMS_DIR")
    @patch("server.audio.alarm.subprocess.Popen")
    def test_picks_random_alarm(
        self, mock_popen, mock_alarms_dir, mock_ffplay, mock_timer
    ) -> None:
        fake_path = MagicMock()
        fake_path.exists.return_value = True
        fake_path.name = "random_alarm.mp3"
        mock_alarms_dir.glob.return_value = [fake_path]
        mock_popen.return_value.pid = 12345

        mock_timer.return_value = MagicMock()

        result = play_alarm(random_alarm=True)

        self.assertEqual(result["status"], "playing")

    @patch("server.audio.alarm._is_ffplay_running", return_value=False)
    @patch("server.audio.alarm.ALARMS_DIR")
    def test_returns_error_when_no_random_alarms_available(
        self, mock_alarms_dir, mock_ffplay
    ) -> None:
        mock_alarms_dir.glob.return_value = []

        result = play_alarm(random_alarm=True)

        self.assertEqual(result["status"], "error")
        self.assertIn("No alarms found", result["message"])


if __name__ == "__main__":
    unittest.main()
