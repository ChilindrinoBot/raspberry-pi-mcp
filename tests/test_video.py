import base64
import unittest
from unittest.mock import Mock, patch

from server.video.video import (
    _get_video_capture_command,
    _remux_to_mp4,
    _record_video_bytes,
    record_video,
    MAX_VIDEO_BYTES,
    MAX_VIDEO_DURATION_SECONDS,
    DEFAULT_FRAMERATE,
)


def _make_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> Mock:
    result = Mock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class GetVideoCommandTests(unittest.TestCase):
    @patch("server.video.video.shutil.which", return_value="/usr/bin/rpicam-vid")
    def test_prefers_rpicam_vid(self, mock_which: Mock) -> None:
        command = _get_video_capture_command("/tmp/video.h264", 5000, 10)

        self.assertIn("/usr/bin/rpicam-vid", command)
        self.assertIn("--output", command)
        self.assertIn("--codec", command)
        self.assertIn("--framerate", command)
        self.assertIn("10", command)
        self.assertIn("--timeout", command)
        self.assertIn("5000", command)
        mock_which.assert_any_call("rpicam-vid")

    @patch("server.video.video.shutil.which", side_effect=[None, "/usr/bin/libcamera-vid"])
    def test_falls_back_to_libcamera_vid(self, mock_which: Mock) -> None:
        command = _get_video_capture_command("/tmp/video.h264", 5000, 10)

        self.assertIn("/usr/bin/libcamera-vid", command)
        self.assertIn("--framerate", command)
        self.assertIn("--timeout", command)
        mock_which.assert_any_call("rpicam-vid")
        mock_which.assert_any_call("libcamera-vid")

    @patch("server.video.video.shutil.which", side_effect=[None, None, "/usr/bin/raspivid"])
    def test_falls_back_to_raspivid(self, mock_which: Mock) -> None:
        command = _get_video_capture_command("/tmp/video.h264", 5000, 10)

        self.assertIn("/usr/bin/raspivid", command)
        self.assertIn("-o", command)
        self.assertIn("-fps", command)
        self.assertIn("10", command)
        self.assertIn("-t", command)
        self.assertIn("5000", command)
        mock_which.assert_any_call("rpicam-vid")
        mock_which.assert_any_call("libcamera-vid")
        mock_which.assert_any_call("raspivid")

    @patch("server.video.video.shutil.which", return_value=None)
    def test_raises_when_no_camera_tool(self, mock_which: Mock) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _get_video_capture_command("/tmp/video.h264", 5000, 10)

        self.assertIn("No video camera available", str(ctx.exception))


class RemuxToMp4Tests(unittest.TestCase):
    @patch("server.video.video.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("server.video.video.subprocess.run", return_value=_make_result())
    def test_remux_success(self, mock_run: Mock, mock_which: Mock) -> None:
        _remux_to_mp4("/tmp/video.h264", "/tmp/video.mp4")

        args = mock_run.call_args[0][0]
        self.assertIn("/usr/bin/ffmpeg", args)
        self.assertIn("/tmp/video.mp4", args)

    @patch("server.video.video.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("server.video.video.subprocess.run", return_value=_make_result())
    def test_remux_passes_input_framerate(self, mock_run: Mock, mock_which: Mock) -> None:
        _remux_to_mp4("/tmp/video.h264", "/tmp/video.mp4", fps=10)

        args = mock_run.call_args[0][0]
        fps_index = args.index("-r")
        self.assertEqual(args[fps_index + 1], "10")
        self.assertLess(fps_index, args.index("-i"))

    @patch("server.video.video.shutil.which", return_value=None)
    def test_remux_raises_when_ffmpeg_missing(self, mock_which: Mock) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _remux_to_mp4("/tmp/video.h264", "/tmp/video.mp4")

        self.assertIn("ffmpeg is not installed", str(ctx.exception))

    @patch("server.video.video.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("server.video.video.subprocess.run", return_value=_make_result(returncode=1, stderr="mux error"))
    def test_remux_failure(self, mock_run: Mock, mock_which: Mock) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _remux_to_mp4("/tmp/video.h264", "/tmp/video.mp4")

        self.assertIn("ffmpeg remux failed", str(ctx.exception))
        self.assertIn("mux error", str(ctx.exception))


class RecordVideoBytesTests(unittest.TestCase):
    @patch("server.video.video.Path.read_bytes", return_value=b"fake mp4 bytes")
    @patch("server.video.video.Path.exists", return_value=True)
    @patch("server.video.video._remux_to_mp4")
    @patch("server.video.video.subprocess.run", return_value=_make_result())
    @patch("server.video.video._get_video_capture_command", return_value=["rpicam-vid"])
    @patch("server.video.video.tempfile.TemporaryDirectory", return_value=Mock(__enter__=Mock(return_value="/tmp/fake_tmp"), __exit__=Mock(return_value=None)))
    def test_record_success_mp4(
        self,
        mock_tmpdir: Mock,
        mock_get_command: Mock,
        mock_run: Mock,
        mock_remux: Mock,
        mock_exists: Mock,
        mock_read_bytes: Mock,
    ) -> None:
        video_bytes, video_format = _record_video_bytes(5, 10)

        self.assertEqual(video_bytes, b"fake mp4 bytes")
        self.assertEqual(video_format, "mp4")
        mock_remux.assert_called_once()
        mock_get_command.assert_called_once()

    @patch("server.video.video.Path.read_bytes", return_value=b"fake h264 bytes")
    @patch("server.video.video.Path.exists", return_value=True)
    @patch("server.video.video._remux_to_mp4", side_effect=RuntimeError("ffmpeg missing"))
    @patch("server.video.video.subprocess.run", return_value=_make_result())
    @patch("server.video.video._get_video_capture_command", return_value=["rpicam-vid"])
    @patch("server.video.video.tempfile.TemporaryDirectory", return_value=Mock(__enter__=Mock(return_value="/tmp/fake_tmp"), __exit__=Mock(return_value=None)))
    def test_record_falls_back_to_h264(
        self,
        mock_tmpdir: Mock,
        mock_get_command: Mock,
        mock_run: Mock,
        mock_remux: Mock,
        mock_exists: Mock,
        mock_read_bytes: Mock,
    ) -> None:
        video_bytes, video_format = _record_video_bytes(5, 10)

        self.assertEqual(video_bytes, b"fake h264 bytes")
        self.assertEqual(video_format, "h264")

    @patch("server.video.video.subprocess.run", return_value=_make_result(returncode=1, stderr="Camera not found"))
    @patch("server.video.video._get_video_capture_command", return_value=["rpicam-vid"])
    @patch("server.video.video.tempfile.TemporaryDirectory", return_value=Mock(__enter__=Mock(return_value="/tmp/fake_tmp"), __exit__=Mock(return_value=None)))
    def test_record_capture_failure(
        self,
        mock_tmpdir: Mock,
        mock_get_command: Mock,
        mock_run: Mock,
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _record_video_bytes(5, 10)

        self.assertIn("Video capture failed", str(ctx.exception))
        self.assertIn("Camera not found", str(ctx.exception))

    @patch("server.video.video.Path.exists", return_value=False)
    @patch("server.video.video.subprocess.run", return_value=_make_result())
    @patch("server.video.video._get_video_capture_command", return_value=["rpicam-vid"])
    @patch("server.video.video.tempfile.TemporaryDirectory", return_value=Mock(__enter__=Mock(return_value="/tmp/fake_tmp"), __exit__=Mock(return_value=None)))
    def test_record_missing_output_file(
        self,
        mock_tmpdir: Mock,
        mock_get_command: Mock,
        mock_run: Mock,
        mock_exists: Mock,
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _record_video_bytes(5, 10)

        self.assertIn("no video file was produced", str(ctx.exception))

    @patch("server.video.video.Path.read_bytes", return_value=b"x" * (MAX_VIDEO_BYTES + 1))
    @patch("server.video.video.Path.exists", return_value=True)
    @patch("server.video.video._remux_to_mp4")
    @patch("server.video.video.subprocess.run", return_value=_make_result())
    @patch("server.video.video._get_video_capture_command", return_value=["rpicam-vid"])
    @patch("server.video.video.tempfile.TemporaryDirectory", return_value=Mock(__enter__=Mock(return_value="/tmp/fake_tmp"), __exit__=Mock(return_value=None)))
    def test_record_exceeds_size_limit(
        self,
        mock_tmpdir: Mock,
        mock_get_command: Mock,
        mock_run: Mock,
        mock_remux: Mock,
        mock_exists: Mock,
        mock_read_bytes: Mock,
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _record_video_bytes(5, 10)

        self.assertIn("exceeds the", str(ctx.exception))


class RecordVideoTests(unittest.TestCase):
    @patch("server.video.video._record_video_bytes", return_value=(b"fake mp4 bytes", "mp4"))
    def test_record_video_success(self, mock_record: Mock) -> None:
        result = record_video(duration_seconds=5, fps=10)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["format"], "mp4")
        self.assertEqual(result["encoding"], "base64")
        self.assertEqual(result["data"], base64.b64encode(b"fake mp4 bytes").decode("ascii"))
        self.assertEqual(result["message"], "Video recorded successfully (5s @10fps).")
        mock_record.assert_called_once_with(5, 10)

    @patch("server.video.video._record_video_bytes", return_value=(b"fake h264 bytes", "h264"))
    def test_record_video_h264_fallback_format(self, mock_record: Mock) -> None:
        result = record_video(duration_seconds=3, fps=10)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["format"], "h264")
        mock_record.assert_called_once_with(3, 10)

    @patch("server.video.video._record_video_bytes", side_effect=RuntimeError("Camera not found"))
    def test_record_video_failure(self, mock_record: Mock) -> None:
        result = record_video(duration_seconds=5)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Camera not found")
        mock_record.assert_called_once_with(5, DEFAULT_FRAMERATE)

    @patch("server.video.video._record_video_bytes", return_value=(b"fake mp4 bytes", "mp4"))
    def test_duration_above_max_is_capped(self, mock_record: Mock) -> None:
        result = record_video(duration_seconds=MAX_VIDEO_DURATION_SECONDS + 10)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], f"Video recorded successfully ({MAX_VIDEO_DURATION_SECONDS}s @10fps).")
        mock_record.assert_called_once_with(MAX_VIDEO_DURATION_SECONDS, DEFAULT_FRAMERATE)

    @patch("server.video.video._record_video_bytes", return_value=(b"fake mp4 bytes", "mp4"))
    def test_duration_below_min_is_raised(self, mock_record: Mock) -> None:
        result = record_video(duration_seconds=0)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Video recorded successfully (1s @10fps).")
        mock_record.assert_called_once_with(1, DEFAULT_FRAMERATE)

    @patch("server.video.video._record_video_bytes", return_value=(b"fake mp4 bytes", "mp4"))
    def test_record_video_default_duration(self, mock_record: Mock) -> None:
        result = record_video()

        self.assertEqual(result["status"], "success")
        mock_record.assert_called_once_with(5, DEFAULT_FRAMERATE)

    @patch("server.video.video._record_video_bytes", return_value=(b"fake mp4 bytes", "mp4"))
    def test_fps_above_max_is_capped(self, mock_record: Mock) -> None:
        result = record_video(duration_seconds=5, fps=300)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Video recorded successfully (5s @30fps).")
        mock_record.assert_called_once_with(5, 30)

    @patch("server.video.video._record_video_bytes", return_value=(b"fake mp4 bytes", "mp4"))
    def test_low_fps_is_kept(self, mock_record: Mock) -> None:
        result = record_video(duration_seconds=5, fps=5)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Video recorded successfully (5s @5fps).")
        mock_record.assert_called_once_with(5, 5)

    @patch("server.video.video._record_video_bytes", return_value=(b"fake mp4 bytes", "mp4"))
    def test_fps_below_min_is_raised(self, mock_record: Mock) -> None:
        result = record_video(duration_seconds=5, fps=0)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Video recorded successfully (5s @1fps).")
        mock_record.assert_called_once_with(5, 1)


if __name__ == "__main__":
    unittest.main()