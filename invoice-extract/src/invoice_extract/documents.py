"""Turn a scanned file on disk into API content blocks.

PDFs go as `document` blocks — the API rasterizes each page and reads it as an
image alongside any embedded text layer, which is what we want for scans. Image
files go as `image` blocks. Nothing is re-encoded locally, so no fidelity is
lost between the scanner and the model.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Iterable

PDF_SUFFIXES = {".pdf"}
IMAGE_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
SUPPORTED_SUFFIXES = PDF_SUFFIXES | set(IMAGE_MEDIA_TYPES)

# The API caps a request at 32 MB. Base64 inflates by 4/3, and the prompt adds
# a little on top, so the file itself must stay comfortably under that.
MAX_FILE_BYTES = 22 * 1024 * 1024


class UnsupportedDocument(ValueError):
    """Raised for a file this tool cannot send to the API."""


def discover(paths: Iterable[Path], recursive: bool = True) -> list[Path]:
    """Expand paths into a sorted list of scannable files.

    Directories are walked; unsupported files inside a directory are skipped
    silently, but an unsupported file named explicitly is an error, because the
    user asked for it by name and would not otherwise learn it was dropped.
    """
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            pattern = "**/*" if recursive else "*"
            for child in sorted(path.glob(pattern)):
                if child.is_file() and child.suffix.lower() in SUPPORTED_SUFFIXES:
                    found.append(child)
        elif path.is_file():
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                raise UnsupportedDocument(
                    f"{path}: unsupported file type {path.suffix!r}. "
                    f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
                )
            found.append(path)
        else:
            raise UnsupportedDocument(f"{path}: no such file or directory")

    # A directory walked twice, or a file named alongside its directory, would
    # otherwise be billed and booked twice.
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in found:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def content_blocks(path: Path) -> list[dict[str, Any]]:
    """Build the content blocks for one scanned file."""
    suffix = path.suffix.lower()
    data = path.read_bytes()

    if not data:
        raise UnsupportedDocument(f"{path}: file is empty")
    if len(data) > MAX_FILE_BYTES:
        raise UnsupportedDocument(
            f"{path}: {len(data) / 1024 / 1024:.1f} MB exceeds the "
            f"{MAX_FILE_BYTES / 1024 / 1024:.0f} MB per-request limit. "
            "Split the file or rescan at a lower DPI."
        )

    encoded = base64.standard_b64encode(data).decode("ascii")

    if suffix in PDF_SUFFIXES:
        return [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": encoded,
                },
            }
        ]

    media_type = IMAGE_MEDIA_TYPES.get(suffix)
    if media_type is None:
        raise UnsupportedDocument(f"{path}: unsupported file type {suffix!r}")
    return [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": encoded,
            },
        }
    ]
