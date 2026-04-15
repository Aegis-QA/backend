from fastapi import APIRouter, File, HTTPException, UploadFile
from app.storage import upload_file_to_minio
import uuid

router = APIRouter()


@router.post("/n8n/persist-upload")
async def persist_upload_for_n8n(
    file: UploadFile = File(None),
    images: list[UploadFile] = File(None),
):
    """Store n8n-uploaded artifacts in MinIO and return normalized object paths.

    This endpoint is intentionally side-effect free for DB tables; it only persists
    raw upload artifacts so workflow nodes can insert metadata into Postgres.
    """
    file_path = None
    original_filename = None
    image_paths: list[str] = []

    if file and file.filename:
        original_filename = file.filename
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "bin"
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        try:
            stored = upload_file_to_minio(file.file, unique_filename)
            file_path = stored or unique_filename
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Document upload failed: {exc}")

    if images and images != [None]:
        for img in images:
            if not img or not img.filename:
                continue

            img_extension = img.filename.split(".")[-1] if "." in img.filename else "bin"
            if img_extension.lower() not in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]:
                continue

            unique_img_name = f"{uuid.uuid4()}.{img_extension}"
            try:
                stored_img = upload_file_to_minio(img.file, unique_img_name)
                image_paths.append(stored_img or unique_img_name)
            except Exception:
                # Continue processing remaining files; caller can inspect uploaded count.
                continue

    if not original_filename:
        if image_paths:
            original_filename = f"📸 {len(image_paths)} image{'s' if len(image_paths) > 1 else ''}"
        else:
            original_filename = "No file"

    return {
        "filename": original_filename,
        "file_path": file_path,
        "image_paths": image_paths,
        "images_uploaded": len(image_paths),
        "has_document": file_path is not None,
    }
