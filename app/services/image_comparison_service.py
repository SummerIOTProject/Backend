from __future__ import annotations

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import AppException, BadGatewayException, BadRequestException, PayloadTooLargeException
from app.schemas.meal_analysis import ImageComparisonAnalysisResponse
from app.services.vision_service import VisionService
from app.utils.files import read_upload_file


class ImageComparisonService:
    def __init__(self) -> None:
        self.vision_service = VisionService()

    async def compare_uploads(
        self,
        *,
        before_image: UploadFile,
        after_image: UploadFile,
        content_length: int | None = None,
    ) -> tuple[str, ImageComparisonAnalysisResponse]:
        self._validate_request_size(content_length)
        before_bytes, before_mime_type, _ = read_upload_file(
            before_image,
            validate_filename_extension=False,
            strict_status=True,
        )
        after_bytes, after_mime_type, _ = read_upload_file(
            after_image,
            validate_filename_extension=False,
            strict_status=True,
        )
        try:
            analysis_type, result = await self.vision_service.compare_images(
                before_image=before_bytes,
                before_mime_type=before_mime_type,
                after_image=after_bytes,
                after_mime_type=after_mime_type,
            )
        except AppException as exc:
            if exc.code == "INVALID_VLM_RESPONSE":
                raise BadGatewayException(message="VLM 응답 형식이 올바르지 않습니다.", code="INVALID_VLM_RESPONSE", detail=exc.detail) from exc
            raise

        if not result.analysis_possible:
            raise BadRequestException(
                message="두 이미지를 비교 분석할 수 없습니다.",
                code="IMAGES_NOT_COMPARABLE",
                detail=result.analysis_impossible_reason or "analysis impossible",
            )

        return analysis_type.value, ImageComparisonAnalysisResponse(
            overall_consumed_ratio=result.overall_consumed_ratio,
            confidence=result.confidence,
            items=result.items,
            summary=result.summary,
            warnings=result.warnings,
        )

    @staticmethod
    def _validate_request_size(content_length: int | None) -> None:
        if content_length is None:
            return
        max_request_size = (settings.MAX_IMAGE_SIZE_MB * 2 * 1024 * 1024) + 65536
        if content_length > max_request_size:
            raise PayloadTooLargeException(
                message="이미지 크기 제한을 초과했습니다.",
                code="IMAGE_TOO_LARGE",
                detail=f"최대 요청 크기 약 {max_request_size} bytes",
            )
