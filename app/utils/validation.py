"""Upload validation helpers."""
from fastapi import HTTPException, UploadFile

from app.config import MAX_UPLOAD_BYTES, ALLOWED_MIME


async def read_image_upload(f: UploadFile, field_name: str) -> bytes:
    """Read an UploadFile, enforce size + mime, return raw bytes."""
    if f.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"{field_name}: unsupported content type '{f.content_type}'. "
                   f"Allowed: {sorted(ALLOWED_MIME)}",
        )

    data = await f.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail=f"{field_name}: empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"{field_name}: file too large "
                   f"({len(data)} bytes > {MAX_UPLOAD_BYTES})",
        )
    return data
