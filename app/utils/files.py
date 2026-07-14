import base64
import io
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings
from app.core.exceptions import BadRequestException

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
FORMAT_BY_MIME = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
EXTENSION_BY_FORMAT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
MIME_BY_FORMAT = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def validate_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise BadRequestException(
            message="지원하지 않는 이미지 형식입니다.",
            code="INVALID_IMAGE_FORMAT",
            detail=f"허용 확장자: {sorted(ALLOWED_EXTENSIONS)}",
        )
    return extension


def validate_mime_type(mime_type: str | None) -> str:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise BadRequestException(
            message="지원하지 않는 이미지 형식입니다.",
            code="INVALID_IMAGE_FORMAT",
            detail=f"허용 MIME 타입: {sorted(ALLOWED_MIME_TYPES)}",
        )
    return str(mime_type)


def validate_file_size(file_bytes: bytes) -> None:
    max_size = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_size:
        raise BadRequestException(
            message="이미지 크기 제한을 초과했습니다.",
            code="IMAGE_TOO_LARGE",
            detail=f"최대 {settings.MAX_IMAGE_SIZE_MB}MB 허용",
        )


def generate_filename(original_filename: str) -> str:
    return f"{uuid.uuid4().hex}{validate_extension(original_filename)}"


def generate_filename_for_extension(extension: str) -> str:
    return f"{uuid.uuid4().hex}{extension}"


def save_image_bytes(*, file_bytes: bytes, filename: str, image_type: str) -> tuple[str, str]:
    ensure_directory(Path(settings.UPLOAD_DIR) / image_type.lower())
    target = Path(settings.UPLOAD_DIR) / image_type.lower() / filename
    target.write_bytes(file_bytes)
    return filename, str(target)


def build_storage_path(image_type: str, filename: str) -> str:
    return f"{image_type.lower()}/{filename}"


def delete_file_if_exists(path_value: str | Path | None) -> None:
    if not path_value:
        return
    path = Path(path_value)
    if path.exists() and path.is_file():
        path.unlink()


def file_to_base64(path: str | Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def read_upload_file(upload_file: UploadFile) -> tuple[bytes, str, str]:
    declared_mime_type = validate_mime_type(upload_file.content_type)
    filename = upload_file.filename or "upload.jpg"
    validate_extension(filename)
    file_bytes = upload_file.file.read()
    validate_file_size(file_bytes)
    upload_file.file.seek(0)
    try:
        Image.open(io.BytesIO(file_bytes)).verify()
        image = Image.open(io.BytesIO(file_bytes))
    except (UnidentifiedImageError, OSError) as exc:
        raise BadRequestException(message="유효하지 않은 이미지 파일입니다.", code="INVALID_IMAGE_FORMAT", detail="Pillow verification failed") from exc
    image = ImageOps.exif_transpose(image)
    image.load()
    detected_format = (image.format or FORMAT_BY_MIME.get(declared_mime_type) or "").upper()
    if detected_format not in EXTENSION_BY_FORMAT:
        raise BadRequestException(message="지원하지 않는 이미지 형식입니다.", code="INVALID_IMAGE_FORMAT", detail=f"detected format={detected_format}")
    max_dimension = max(image.size)
    if max_dimension > settings.ANALYSIS_IMAGE_MAX_DIMENSION:
        image.thumbnail((settings.ANALYSIS_IMAGE_MAX_DIMENSION, settings.ANALYSIS_IMAGE_MAX_DIMENSION))
    output = io.BytesIO()
    save_format = detected_format
    save_kwargs = {}
    if save_format == "JPEG":
        image = image.convert("RGB")
        save_kwargs["quality"] = settings.ANALYSIS_IMAGE_JPEG_QUALITY
        save_kwargs["optimize"] = True
    elif save_format == "WEBP":
        save_kwargs["quality"] = settings.ANALYSIS_IMAGE_JPEG_QUALITY
    image.save(output, format=save_format, **save_kwargs)
    processed_bytes = output.getvalue()
    validate_file_size(processed_bytes)
    actual_mime_type = MIME_BY_FORMAT[save_format]
    return processed_bytes, actual_mime_type, EXTENSION_BY_FORMAT[save_format]


def resolve_storage_path(stored_path: str) -> Path:
    safe_root = Path(settings.UPLOAD_DIR).resolve()
    candidate = (safe_root / stored_path).resolve()
    if not str(candidate).startswith(str(safe_root)):
        raise BadRequestException(message="잘못된 파일 경로입니다.", code="IMAGE_NOT_FOUND", detail="invalid storage path")
    return candidate
