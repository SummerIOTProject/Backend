from app.services.storage.factory import build_image_storage


def ensure_upload_storage_ready() -> None:
    build_image_storage().ensure_ready()


def validate_storage_configuration() -> None:
    build_image_storage().validate_configuration()
