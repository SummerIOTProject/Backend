from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_rfid_service
from app.core.exceptions import ForbiddenException
from app.core.security import require_active_user, require_admin
from app.schemas.common import CommonResponse
from app.schemas.rfid import RfidCardCreateRequest, RfidCardResponse, RfidScanRequest, RfidScanResponse
from app.schemas.user import UserResponse
from app.services.rfid_service import RfidService

router = APIRouter(prefix="/rfid-cards", tags=["RFID"])


@router.post(
    "",
    summary="RFID 카드 등록",
    description="사용자에게 RFID 카드를 등록합니다.",
    response_model=CommonResponse[RfidCardResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_rfid_card(
    request: RfidCardCreateRequest,
    service: RfidService = Depends(get_rfid_service),
    current_user=Depends(require_active_user),
):
    if current_user.role != "ADMIN" and request.user_id != current_user.id:
        raise ForbiddenException(
            message="본인 계정에만 RFID 카드를 연결할 수 있습니다.",
            code="RFID_FORBIDDEN",
            detail=f"user_id={request.user_id}, current_user_id={current_user.id}",
        )
    card = service.register_card(request)
    return CommonResponse(success=True, message="RFID 카드가 등록되었습니다.", data=RfidCardResponse.model_validate(card))


@router.post(
    "/scan",
    summary="RFID 스캔",
    description="RFID UID를 스캔하여 사용자와 카드를 조회합니다.",
    response_model=CommonResponse[RfidScanResponse],
    status_code=status.HTTP_200_OK,
)
def scan_rfid(request: RfidScanRequest, service: RfidService = Depends(get_rfid_service)):
    card = service.scan_card(request)
    data = RfidScanResponse(card=RfidCardResponse.model_validate(card), user=UserResponse.model_validate(card.user))
    return CommonResponse(success=True, message="RFID 스캔이 완료되었습니다.", data=data)


@router.patch(
    "/{card_id}/deactivate",
    summary="RFID 카드 비활성화",
    description="RFID 카드를 비활성화합니다.",
    response_model=CommonResponse[RfidCardResponse],
    status_code=status.HTTP_200_OK,
)
def deactivate_card(
    card_id: int,
    service: RfidService = Depends(get_rfid_service),
    _: object = Depends(require_admin),
):
    card = service.deactivate_card(card_id)
    return CommonResponse(success=True, message="RFID 카드가 비활성화되었습니다.", data=RfidCardResponse.model_validate(card))
