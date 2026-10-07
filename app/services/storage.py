import shutil
from pathlib import Path

from fastapi import UploadFile

from app.config import MAX_UPLOAD_BYTES, UPLOAD_DIR


def save_upload(file_id: str, upload: UploadFile, suffix: str) -> Path:
    """Stream to disk (never load whole file in memory) and enforce size limit."""
    folder = UPLOAD_DIR / file_id
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"original{suffix}"
    size = 0
    with dest.open("wb") as out:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                shutil.rmtree(folder, ignore_errors=True)
                raise ValueError("File too large")
            out.write(chunk)
    return dest
