from __future__ import annotations

import time
from pathlib import Path

from ... import mcp
from . import config
from . import http
from . import images


@mcp.resource("cube://contents")
def list_cube_contents() -> str:
    """
    Returns a list of the files (gifs and images) stored on the Cube display,
    with sizes in KB.
    """
    if not config.CUBE_BASE_URL:
        return "CUBE_BASE_URL is not configured. Set it in the .env file."

    try:
        files = http._fetch_cube_files()
    except Exception as e:
        return f"Failed to fetch contents from Cube: {e}"

    if not files:
        return "No files found on the Cube."

    lines = [f"{name} ({size_kb} KB)" for name, size_kb in files]
    return "Available Cube files:\n" + "\n".join(lines)


@mcp.tool()
def delete_cube_file(filename: str) -> dict[str, str]:
    """
    Deletes a file stored in the Cube's memory (not the local gallery).

    Looks the file up by name in the Cube's file list, requests the deletion
    via the Cube's /delete endpoint and confirms the file is gone from the
    file list before reporting success.
    """
    if not config.CUBE_BASE_URL:
        return {
            "status": "error",
            "message": "CUBE_BASE_URL is not configured. Set it in the .env file.",
        }

    key = filename.strip().lstrip("/")
    try:
        files = http._fetch_cube_files()
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch contents from Cube: {e}"}

    matches = [name for name, _size_kb in files if name.lower() == key.lower()]
    if not matches:
        return {"status": "error", "message": f"{filename} was not found on the Cube."}
    target = matches[0]

    try:
        http._delete_cube_file(target)
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete {target} from Cube: {e}"}

    # The device updates its file index lazily, so give it a few chances
    # before reporting the deletion as unconfirmed.
    for _attempt in range(3):
        try:
            remaining = http._fetch_cube_files()
        except Exception as e:
            return {"status": "error", "message": f"Failed to verify deletion of {target} on Cube: {e}"}

        if not any(name.lower() == target.lower() for name, _size_kb in remaining):
            return {"status": "success", "message": f"Deleted {target} from Cube."}

        time.sleep(1)

    return {
        "status": "error",
        "message": f"Deletion of {target} could not be confirmed: the Cube still lists it.",
    }


@mcp.tool()
def clear_cube_contents() -> dict[str, str]:
    """
    Clears all files from the Cube's memory (not the local gallery).

    Sends GET /set?clear=image to the Cube and confirms the file list is
    empty before reporting success.
    """
    if not config.CUBE_BASE_URL:
        return {
            "status": "error",
            "message": "CUBE_BASE_URL is not configured. Set it in the .env file.",
        }

    try:
        files_before = http._fetch_cube_files()
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch contents from Cube: {e}"}

    if not files_before:
        return {"status": "success", "message": "No files to clear on Cube."}

    count = len(files_before)
    try:
        http._clear_cube_contents_request()
    except Exception as e:
        return {"status": "error", "message": f"Failed to clear Cube contents: {e}"}

    for _attempt in range(3):
        try:
            remaining = http._fetch_cube_files()
        except Exception as e:
            return {"status": "error", "message": f"Failed to verify clear on Cube: {e}"}

        if not remaining:
            return {"status": "success", "message": f"Cleared {count} files from Cube."}

        time.sleep(1)

    return {
        "status": "error",
        "message": f"Clear could not be confirmed: the Cube still lists {len(remaining)} files.",
    }


@mcp.resource("cube://free-space")
def get_cube_free_space() -> str:
    """
    Returns the free storage space available on the Cube display.
    """
    if not config.CUBE_BASE_URL:
        return "CUBE_BASE_URL is not configured. Set it in the .env file."

    try:
        free, total = http._fetch_cube_space()
    except Exception as e:
        return f"Failed to fetch free space from Cube: {e}"

    return f"Free space on Cube: {free // 1024} KB (total: {total // 1024} KB)"


@mcp.tool()
def upload_cube_image(data: str, filename: str) -> dict[str, str]:
    """
    Uploads a gif or jpg/jpeg image to the Cube display.

    The image bytes must be Base64-encoded by the client. After decoding, the
    file is validated: allowed extension (.gif, .jpg, .jpeg), dimensions
    exactly 240x240, and enough free space on the Cube before uploading it to
    the /image directory via /doUpload. Other formats (png, webp, bmp...) are
    not rejected: they are automatically converted to an exact 240x240 JPEG
    and their name gets a .jpg suffix.

    Args:
        data: Image bytes encoded in Base64 (client-side).
        filename: Name of the image, used to determine its type.
    """
    if not config.CUBE_BASE_URL:
        return {"status": "error", "message": "CUBE_BASE_URL is not configured. Set it in the .env file."}

    name = Path(filename.strip()).name
    if not name:
        return {"status": "error", "message": "Filename is required."}

    try:
        payload = images._decode_image(data)
    except Exception as e:
        return {"status": "error", "message": f"Failed to decode image {name}: {e}"}

    if not payload:
        return {"status": "error", "message": f"Image is empty: {name}."}

    name, payload, conversion_error = images._to_cube_compatible_image(name, payload)
    if conversion_error:
        return {"status": "error", "message": conversion_error}

    dimensions = images._image_dimensions(payload)
    if dimensions is None:
        return {"status": "error", "message": f"Could not read image dimensions of {name}."}

    if dimensions != config.IMAGE_REQUIRED_DIMENSIONS:
        width, height = dimensions
        return {
            "status": "error",
            "message": (
                f"Image must be {config.IMAGE_REQUIRED_DIMENSIONS[0]}x{config.IMAGE_REQUIRED_DIMENSIONS[1]} "
                f"(got {width}x{height}): {name}."
            ),
        }

    rejection = images._cube_free_space_rejection(len(payload))
    if rejection:
        return {"status": "error", "message": rejection}

    try:
        http._upload_cube_image(name, payload)
    except Exception as e:
        return {"status": "error", "message": f"Failed to upload image to Cube: {e}"}

    try:
        available = http._fetch_cube_gifs()
    except Exception as e:
        return {"status": "error", "message": f"Failed to verify upload of {name} on Cube: {e}"}

    if not images._is_in_cube_filelist(name, available):
        return {
            "status": "error",
            "message": f"Upload could not be confirmed: {name} is not in the Cube file list.",
        }

    return {"status": "success", "message": f"Image uploaded to Cube: {name}"}
