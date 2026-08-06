import base64
import unittest
from unittest.mock import Mock, patch

from server.image.image import (
    _get_camera_command,
    _capture_photo_bytes,
    take_photo,
    MAX_PHOTO_BYTES,
)


def _make_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> Mock:
    result = Mock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class GetCameraCommandTests(unittest.TestCase):
    @patch("server.image.image.shutil.which", return_value="/usr/bin/rpicam-still")
    def test_prefers_rpicam_still(self, mock_which: Mock) -> None:
        command = _get_camera_command()

        self.assertIn("/usr/bin/rpicam-still", command)
        self.assertIn("--output", command)
        self.assertIn("{output}", command)
        mock_which.assert_any_call("rpicam-still")

    @patch("server.image.image.shutil.which", side_effect=[None, "/usr/bin/libcamera-still"])
    def test_falls_back_to_libcamera_still(self, mock_which: Mock) -> None:
        command = _get_camera_command()

        self.assertIn("/usr/bin/libcamera-still", command)
        self.assertIn("--output", command)
        self.assertIn("{output}", command)
        mock_which.assert_any_call("rpicam-still")
        mock_which.assert_any_call("libcamera-still")

    @patch("server.image.image.shutil.which", side_effect=[None, None, "/usr/bin/raspistill"])
    def test_falls_back_to_raspistill(self, mock_which: Mock) -> None:
        command = _get_camera_command()

        self.assertIn("/usr/bin/raspistill", command)
        self.assertIn("-o", command)
        self.assertIn("{output}", command)
        mock_which.assert_any_call("rpicam-still")
        mock_which.assert_any_call("libcamera-still")
        mock_which.assert_any_call("raspistill")

    @patch("server.image.image.shutil.which", return_value=None)
    def test_raises_when_no_camera_tool(self, mock_which: Mock) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _get_camera_command()

        self.assertIn("No camera capture tool found", str(ctx.exception))


class CapturePhotoBytesTests(unittest.TestCase):
    @patch("server.image.image.Path.read_bytes", return_value=b"fake jpeg bytes")
    @patch("server.image.image.Path.exists", return_value=True)
    @patch("server.image.image.subprocess.run", return_value=_make_result())
    @patch("server.image.image._get_camera_command", return_value=["libcamera-still", "--output", "{output}", "--nopreview"])
    @patch("server.image.image.tempfile.TemporaryDirectory", return_value=Mock(__enter__=Mock(return_value="/tmp/fake_tmp"), __exit__=Mock(return_value=None)))
    def test_capture_success(
        self,
        mock_tmpdir: Mock,
        mock_get_command: Mock,
        mock_run: Mock,
        mock_exists: Mock,
        mock_read_bytes: Mock,
    ) -> None:
        photo_bytes = _capture_photo_bytes()

        self.assertEqual(photo_bytes, b"fake jpeg bytes")
        mock_get_command.assert_called_once()
        mock_run.assert_called_once()
        mock_exists.assert_called_once()
        mock_read_bytes.assert_called_once()

    @patch("server.image.image.subprocess.run", return_value=_make_result(returncode=1, stderr="Camera not found"))
    @patch("server.image.image._get_camera_command", return_value=["libcamera-still", "--output", "{output}", "--nopreview"])
    @patch("server.image.image.tempfile.TemporaryDirectory", return_value=Mock(__enter__=Mock(return_value="/tmp/fake_tmp"), __exit__=Mock(return_value=None)))
    def test_capture_failure(
        self,
        mock_tmpdir: Mock,
        mock_get_command: Mock,
        mock_run: Mock,
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _capture_photo_bytes()

        self.assertIn("Camera capture failed", str(ctx.exception))
        self.assertIn("Camera not found", str(ctx.exception))

    @patch("server.image.image.Path.exists", return_value=False)
    @patch("server.image.image.subprocess.run", return_value=_make_result())
    @patch("server.image.image._get_camera_command", return_value=["libcamera-still", "--output", "{output}", "--nopreview"])
    @patch("server.image.image.tempfile.TemporaryDirectory", return_value=Mock(__enter__=Mock(return_value="/tmp/fake_tmp"), __exit__=Mock(return_value=None)))
    def test_capture_missing_output_file(
        self,
        mock_tmpdir: Mock,
        mock_get_command: Mock,
        mock_run: Mock,
        mock_exists: Mock,
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _capture_photo_bytes()

        self.assertIn("no photo file was produced", str(ctx.exception))

    @patch("server.image.image.Path.read_bytes", return_value=b"x" * (MAX_PHOTO_BYTES + 1))
    @patch("server.image.image.Path.exists", return_value=True)
    @patch("server.image.image.subprocess.run", return_value=_make_result())
    @patch("server.image.image._get_camera_command", return_value=["libcamera-still", "--output", "{output}", "--nopreview"])
    @patch("server.image.image.tempfile.TemporaryDirectory", return_value=Mock(__enter__=Mock(return_value="/tmp/fake_tmp"), __exit__=Mock(return_value=None)))
    def test_capture_exceeds_size_limit(
        self,
        mock_tmpdir: Mock,
        mock_get_command: Mock,
        mock_run: Mock,
        mock_exists: Mock,
        mock_read_bytes: Mock,
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _capture_photo_bytes()

        self.assertIn("exceeds the", str(ctx.exception))


class TakePhotoTests(unittest.TestCase):
    @patch("server.image.image._capture_photo_bytes", return_value=b"fake jpeg bytes")
    def test_take_photo_success(self, mock_capture: Mock) -> None:
        result = take_photo()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["format"], "jpeg")
        self.assertEqual(result["encoding"], "base64")
        self.assertEqual(result["data"], base64.b64encode(b"fake jpeg bytes").decode("ascii"))
        self.assertEqual(result["message"], "Photo captured successfully.")
        mock_capture.assert_called_once()

    @patch("server.image.image._capture_photo_bytes", side_effect=RuntimeError("Camera not found"))
    def test_take_photo_failure(self, mock_capture: Mock) -> None:
        result = take_photo()

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Camera not found")
        mock_capture.assert_called_once()


if __name__ == "__main__":
    unittest.main()