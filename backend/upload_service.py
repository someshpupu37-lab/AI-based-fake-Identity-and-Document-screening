from pathlib import Path
import shutil
import uuid

from fastapi import UploadFile, HTTPException


UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"

UPLOAD_DIR.mkdir(exist_ok=True)


ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def save_uploaded_file(
    file: UploadFile
) -> dict:

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP files are allowed."
        )

    extension = ALLOWED_TYPES[file.content_type]

    unique_name = (
        f"{uuid.uuid4().hex}{extension}"
    )

    file_path = UPLOAD_DIR / unique_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    return {
        "filename": file.filename,
        "saved_filename": unique_name,
        "path": str(file_path),
        "content_type": file.content_type
    }