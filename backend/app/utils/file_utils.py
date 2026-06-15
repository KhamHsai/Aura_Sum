import os
import uuid
from pathlib import Path
from typing import Tuple

# Allowed MIME types and extensions
ALLOWED_MIMETYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".pdf",
}

def validate_receipt_file(
    filename: str,
    content_type: str,
    file_bytes: bytes,
    max_size_bytes: int,
) -> None:
    """
    Validate that:
    1. Original filename is provided and valid.
    2. Extension is allowed.
    3. MIME type is allowed.
    4. File is not empty.
    5. File size is within the configured limit.
    """
    if not filename or not filename.strip():
        raise ValueError("Invalid receipt filename")

    # Check extension
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported receipt file type")

    # Check MIME type
    if content_type.lower() not in ALLOWED_MIMETYPES:
        raise ValueError("Unsupported receipt file type")

    # Check empty
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("Receipt file is empty")

    # Check size
    if len(file_bytes) > max_size_bytes:
        raise ValueError("Receipt file is too large")

def generate_stored_filename(original_filename: str) -> str:
    """
    Generate a safe unique filename: UUID + original lowercase extension.
    """
    suffix = Path(original_filename).suffix.lower()
    if suffix == ".jpeg":
        suffix = ".jpeg"
    return f"{uuid.uuid4()}{suffix}"

def save_receipt_file(
    file_bytes: bytes,
    stored_filename: str,
    upload_dir: str,
) -> str:
    """
    Save validated bytes into the upload directory.
    Creates directory if it doesn't exist.
    Returns the file path.
    """
    upload_path = Path(upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_path / stored_filename
    file_path.write_bytes(file_bytes)
    return str(file_path)

def delete_saved_file(file_path: str) -> None:
    """
    Delete a file if it exists.
    """
    if file_path:
        p = Path(file_path)
        if p.exists() and p.is_file():
            p.unlink()