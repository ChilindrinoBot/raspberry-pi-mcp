import base64
import unittest
from io import BytesIO
from unittest.mock import Mock, patch

from PIL import Image

from server.display.cube import (
    list_cube_contents,
    delete_cube_file,
    clear_cube_contents,
    get_cube_free_space,
    upload_cube_image,
    _image_dimensions,
    _delete_cube_file,
    _clear_cube_contents_request,
)


def _image_bytes(fmt: str, width: int, height: int) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format=fmt)
    return buffer.getvalue()


class ListCubeContentsTests(unittest.TestCase):
    @patch(
        "server.display.cube.http._fetch_cube_files",
        return_value=[("gif1.gif", 460), ("image1.jpg", 12)],
    )
    def test_returns_file_list_with_sizes(self, mock_fetch: Mock) -> None:
        result = list_cube_contents()

        self.assertIn("Available Cube files:", result)
        self.assertIn("gif1.gif (460 KB)", result)
        self.assertIn("image1.jpg (12 KB)", result)
        mock_fetch.assert_called_once()

    def test_returns_not_configured_when_no_base_url(self) -> None:
        with patch("server.display.cube.config.CUBE_BASE_URL", ""):
            result = list_cube_contents()

        self.assertIn("CUBE_BASE_URL is not configured", result)

    @patch("server.display.cube.http._fetch_cube_files", return_value=[])
    def test_returns_no_gifs_found_when_empty(self, mock_fetch: Mock) -> None:
        result = list_cube_contents()

        self.assertEqual(result, "No files found on the Cube.")
        mock_fetch.assert_called_once()

    @patch("server.display.cube.http._fetch_cube_files", side_effect=RuntimeError("timeout"))
    def test_returns_error_on_fetch_failure(self, mock_fetch: Mock) -> None:
        result = list_cube_contents()

        self.assertIn("Failed to fetch contents from Cube", result)
        self.assertIn("timeout", result)
        mock_fetch.assert_called_once()


class DeleteCubeFileTests(unittest.TestCase):
    @patch("server.display.cube.http._delete_cube_file")
    @patch(
        "server.display.cube.http._fetch_cube_files",
        side_effect=[[("tmp.gif", 460), ("old.jpg", 12)], [("old.jpg", 12)]],
    )
    def test_deletes_file_and_confirms(
        self, mock_fetch: Mock, mock_delete: Mock
    ) -> None:
        result = delete_cube_file("tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertIn("Deleted tmp.gif from Cube.", result["message"])
        mock_delete.assert_called_once_with("tmp.gif")
        self.assertEqual(mock_fetch.call_count, 2)

    @patch("server.display.cube.http._delete_cube_file")
    @patch("server.display.cube.http._fetch_cube_files", return_value=[("other.gif", 460)])
    def test_rejects_when_file_not_found(self, mock_fetch: Mock, mock_delete: Mock) -> None:
        result = delete_cube_file("missing.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("missing.gif was not found on the Cube.", result["message"])
        mock_delete.assert_not_called()

    @patch("server.display.cube.http._delete_cube_file", side_effect=RuntimeError("boom"))
    @patch("server.display.cube.http._fetch_cube_files", return_value=[("tmp.gif", 460)])
    def test_reports_error_when_delete_request_fails(
        self, mock_fetch: Mock, mock_delete: Mock
    ) -> None:
        result = delete_cube_file("tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to delete tmp.gif from Cube", result["message"])
        self.assertIn("boom", result["message"])

    @patch("server.display.cube.http._delete_cube_file")
    @patch(
        "server.display.cube.http._fetch_cube_files",
        side_effect=[[("tmp.gif", 460)], [("tmp.gif", 460)], [("tmp.gif", 460)], [("tmp.gif", 460)]],
    )
    def test_reports_error_when_file_still_listed_after_delete(
        self, mock_fetch: Mock, mock_delete: Mock
    ) -> None:
        result = delete_cube_file("/tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("could not be confirmed", result["message"])
        self.assertIn("still lists it", result["message"])
        mock_delete.assert_called_once_with("tmp.gif")
        self.assertEqual(mock_fetch.call_count, 4)

    def test_helper_targets_image_dir_with_encoded_path(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            _delete_cube_file("my file.gif")

        requested = mock_urlopen.call_args[0][0]
        self.assertIn("/delete?file=%2Fimage%2Fmy%20file.gif", requested)

    def test_helper_does_not_duplicate_image_prefix(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            _delete_cube_file("/image/tmp.gif")

        requested = mock_urlopen.call_args[0][0]
        self.assertIn("/delete?file=%2Fimage%2Ftmp.gif", requested)

    def test_helper_raises_on_request_failure(self) -> None:
        with patch(
            "server.display.cube.http.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("connection refused"),
        ):
            with self.assertRaises(Exception) as ctx:
                _delete_cube_file("tmp.gif")

        self.assertIn("connection refused", str(ctx.exception))


class ClearCubeContentsTests(unittest.TestCase):
    @patch("server.display.cube.http._clear_cube_contents_request")
    @patch(
        "server.display.cube.http._fetch_cube_files",
        side_effect=[[("tmp.gif", 460), ("old.jpg", 12)], []],
    )
    def test_clears_and_confirms_empty(self, mock_fetch: Mock, mock_clear: Mock) -> None:
        result = clear_cube_contents()

        self.assertEqual(result["status"], "success")
        self.assertIn("Cleared 2 files from Cube.", result["message"])
        mock_clear.assert_called_once()
        self.assertEqual(mock_fetch.call_count, 2)

    @patch("server.display.cube.http._clear_cube_contents_request")
    @patch("server.display.cube.http._fetch_cube_files", return_value=[])
    def test_returns_no_files_when_empty(self, mock_fetch: Mock, mock_clear: Mock) -> None:
        result = clear_cube_contents()

        self.assertEqual(result["status"], "success")
        self.assertIn("No files to clear", result["message"])
        mock_clear.assert_not_called()

    @patch("server.display.cube.http._clear_cube_contents_request", side_effect=RuntimeError("boom"))
    @patch(
        "server.display.cube.http._fetch_cube_files",
        return_value=[("tmp.gif", 460)],
    )
    def test_reports_error_when_clear_request_fails(self, mock_fetch: Mock, mock_clear: Mock) -> None:
        result = clear_cube_contents()

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to clear Cube contents", result["message"])
        self.assertIn("boom", result["message"])

    @patch("server.display.cube.http._clear_cube_contents_request")
    @patch(
        "server.display.cube.http._fetch_cube_files",
        side_effect=[
            [("tmp.gif", 460)],
            [("tmp.gif", 460)],
            [("tmp.gif", 460)],
            [("tmp.gif", 460)],
        ],
    )
    def test_reports_error_when_still_listed_after_clear(
        self, mock_fetch: Mock, mock_clear: Mock
    ) -> None:
        result = clear_cube_contents()

        self.assertEqual(result["status"], "error")
        self.assertIn("could not be confirmed", result["message"])
        self.assertIn("still lists", result["message"])
        self.assertEqual(mock_fetch.call_count, 4)

    def test_helper_sends_clear_request(self) -> None:
        with patch("server.display.cube.http.urllib.request.urlopen") as mock_urlopen:
            _clear_cube_contents_request()

        requested = mock_urlopen.call_args[0][0]
        self.assertIn("/set?clear=image", requested)


class GetCubeFreeSpaceTests(unittest.TestCase):
    @patch("server.display.cube.http._fetch_cube_space", return_value=(925196, 3121152))
    def test_returns_free_space_in_kb(self, mock_fetch: Mock) -> None:
        result = get_cube_free_space()

        self.assertIn("Free space on Cube:", result)
        self.assertIn("903 KB", result)
        self.assertIn("total: 3048 KB", result)
        mock_fetch.assert_called_once()

    def test_returns_not_configured_when_no_base_url(self) -> None:
        with patch("server.display.cube.config.CUBE_BASE_URL", ""):
            result = get_cube_free_space()

        self.assertIn("CUBE_BASE_URL is not configured", result)

    @patch("server.display.cube.http._fetch_cube_space", side_effect=RuntimeError("timeout"))
    def test_returns_error_on_fetch_failure(self, mock_fetch: Mock) -> None:
        result = get_cube_free_space()

        self.assertIn("Failed to fetch free space from Cube", result)
        self.assertIn("timeout", result)
        mock_fetch.assert_called_once()


class UploadCubeImageTests(unittest.TestCase):
    def _encoded(self, data: bytes) -> str:
        return base64.b64encode(data).decode()

    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["image/tmp.gif", "image/test.jpg"])
    @patch("server.display.cube.http._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube.http._upload_cube_image")
    def test_success_with_encoded_gif_confirms_in_filelist(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Image uploaded to Cube: tmp.gif")
        mock_space.assert_called_once()
        filename, payload = mock_upload.call_args[0]
        self.assertEqual(filename, "tmp.gif")
        self.assertEqual(payload, _image_bytes("GIF", 240, 240))
        mock_gifs.assert_called_once()

    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["image/photo.jpg"])
    @patch("server.display.cube.http._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube.http._upload_cube_image")
    def test_success_with_encoded_jpg(self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("JPEG", 240, 240)), "photo.jpg")

        self.assertEqual(result["status"], "success")
        self.assertIn("Image uploaded to Cube: photo.jpg", result["message"])

    def test_returns_error_when_not_configured(self) -> None:
        with patch("server.display.cube.config.CUBE_BASE_URL", ""):
            result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("CUBE_BASE_URL is not configured", result["message"])

    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["image/photo.jpg"])
    @patch("server.display.cube.http._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube.http._upload_cube_image")
    def test_converts_png_to_exact_240_jpeg_instead_of_rejecting(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("PNG", 500, 300)), "photo.png")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Image uploaded to Cube: photo.jpg")
        uploaded_name, payload = mock_upload.call_args[0]
        self.assertEqual(uploaded_name, "photo.jpg")
        with Image.open(BytesIO(payload)) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(img.size, (240, 240))

    @patch("server.display.cube.http._fetch_cube_space")
    def test_returns_error_when_conversion_fails(self, mock_space: Mock) -> None:
        result = upload_cube_image(self._encoded(b"data"), "picture.webp")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to convert image picture.webp to JPEG", result["message"])
        mock_space.assert_not_called()

    def test_returns_error_when_nameless_format_cannot_be_converted(self) -> None:
        result = upload_cube_image(self._encoded(b"data"), "noext")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to convert image noext to JPEG", result["message"])

    def test_converts_png_keeping_basename_with_jpg_suffix(self) -> None:
        with patch("server.display.cube.http._fetch_cube_gifs", return_value=["image/tmp.jpg"]):
            with patch("server.display.cube.http._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024)):
                with patch("server.display.cube.http._upload_cube_image") as mock_upload:
                    result = upload_cube_image(
                        self._encoded(_image_bytes("PNG", 300, 300)), "/etc/passwd/tmp.PNG"
                    )

        self.assertEqual(result["status"], "success")
        self.assertEqual(mock_upload.call_args[0][0], "tmp.jpg")

    def test_rejects_empty_filename(self) -> None:
        result = upload_cube_image(self._encoded(b"data"), "  ")

        self.assertEqual(result["status"], "error")
        self.assertIn("Filename is required", result["message"])

    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["image/tmp.gif"])
    @patch("server.display.cube.http._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube.http._upload_cube_image")
    def test_uses_basename_of_sent_filename(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "/etc/passwd/tmp.gif")

        self.assertEqual(result["status"], "success")
        self.assertEqual(mock_upload.call_args[0][0], "tmp.gif")

    def test_rejects_malformed_base64(self) -> None:
        result = upload_cube_image("not-valid-base64!!!", "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to decode image tmp.gif", result["message"])

    @patch("server.display.cube.images._decode_image", return_value=b"")
    def test_rejects_empty_payload(self, mock_decode: Mock) -> None:
        result = upload_cube_image("token", "empty.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image is empty: empty.gif", result["message"])

    @patch("server.display.cube.http._fetch_cube_space")
    def test_rejects_wrong_dimensions(self, mock_space: Mock) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 100, 100)), "small.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Image must be 240x240", result["message"])
        self.assertIn("(got 100x100)", result["message"])
        mock_space.assert_not_called()

    @patch("server.display.cube.http._fetch_cube_space")
    def test_rejects_undetectable_dimensions(self, mock_space: Mock) -> None:
        result = upload_cube_image(self._encoded(b"GIF89a\xff\xff"), "broken.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Could not read image dimensions of broken.gif", result["message"])
        mock_space.assert_not_called()

    @patch("server.display.cube.http._upload_cube_image")
    @patch("server.display.cube.http._fetch_cube_space", return_value=(10, 3 * 1024 * 1024))
    def test_rejects_when_not_enough_space(self, mock_space: Mock, mock_upload: Mock) -> None:
        data = _image_bytes("GIF", 240, 240) + b"x" * 100

        result = upload_cube_image(self._encoded(data), "big.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Not enough space on Cube", result["message"])
        self.assertIn(f"needs {len(data)} bytes", result["message"])
        self.assertIn("only 10 bytes (0.0 KB) are free", result["message"])
        mock_upload.assert_not_called()

    @patch("server.display.cube.http._fetch_cube_space", side_effect=RuntimeError("timeout"))
    def test_returns_error_when_space_check_fails(self, mock_space: Mock) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to check free space on Cube", result["message"])

    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["image/tmp.gif"])
    @patch("server.display.cube.http._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube.http._upload_cube_image", side_effect=RuntimeError("connection refused"))
    def test_returns_error_when_upload_fails(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to upload image to Cube", result["message"])
        mock_gifs.assert_not_called()

    @patch("server.display.cube.http._fetch_cube_gifs", side_effect=RuntimeError("timeout"))
    @patch("server.display.cube.http._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube.http._upload_cube_image")
    def test_returns_error_when_confirmation_fails(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "tmp.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to verify upload of tmp.gif on Cube", result["message"])

    @patch("server.display.cube.http._fetch_cube_gifs", return_value=["image/tmp.gif", "image/other.jpg"])
    @patch("server.display.cube.http._fetch_cube_space", return_value=(1024 * 1024, 3 * 1024 * 1024))
    @patch("server.display.cube.http._upload_cube_image")
    def test_returns_error_when_file_not_in_filelist(
        self, mock_upload: Mock, mock_space: Mock, mock_gifs: Mock
    ) -> None:
        result = upload_cube_image(self._encoded(_image_bytes("GIF", 240, 240)), "missing.gif")

        self.assertEqual(result["status"], "error")
        self.assertIn("Upload could not be confirmed", result["message"])
        self.assertIn("missing.gif is not in the Cube file list", result["message"])


if __name__ == "__main__":
    unittest.main()
