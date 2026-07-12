import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequestException

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def validate_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise BadRequestException(
            message="지원하지 않는 이미지 확장자입니다.",
            code="INVALID_IMAGE_TYPE",
            detail=f"허용 확장자: {sorted(ALLOWED_EXTENSIONS)}",
        )
    return extension


def validate_mime_type(content_type: str | None) -> str:
    if content_type not in ALLOWED_MIME_TYPES:
        raise BadRequestException(
            message="지원하지 않는 이미지 MIME 타입입니다.",
            code="INVALID_IMAGE_TYPE",
            detail=f"허용 MIME 타입: {sorted(ALLOWED_MIME_TYPES)}",
        )
    return str(content_type)


def generate_unique_filename(original_filename: str) -> str:
    extension = validate_extension(original_filename)
    return f"{uuid.uuid4().hex}{extension}"


def validate_file_size(file_bytes: bytes) -> None:
    max_size = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_size:
        raise BadRequestException(
            message="이미지 크기 제한을 초과했습니다.",
            code="IMAGE_TOO_LARGE",
            detail=f"최대 허용 크기: {settings.MAX_IMAGE_SIZE_MB}MB",
        )


def save_upload_file(file: UploadFile, destination_dir: Path) -> tuple[str, str]:
    validate_mime_type(file.content_type)
    generated_name = generate_unique_filename(file.filename or "upload.jpg")
    ensure_directory(destination_dir)
    destination = destination_dir / generated_name
    file.file.seek(0)
    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return generated_name, str(destination)


def save_bytes_file(file_bytes: bytes, filename: str, destination_dir: Path) -> tuple[str, str]:
    generated_name = generate_unique_filename(filename)
    ensure_directory(destination_dir)
    destination = destination_dir / generated_name
    destination.write_bytes(file_bytes)
    return generated_name, str(destination)


def delete_file_if_exists(file_path: str | Path | None) -> None:
    if not file_path:
        return
    path = Path(file_path)
    if path.exists() and path.is_file():
        path.unlink()


def build_upload_url(subdir: str, filename: str) -> str:
    return f"/uploads/{subdir}/{filename}"
