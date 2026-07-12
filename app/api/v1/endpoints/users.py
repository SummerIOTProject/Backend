from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_user_service
from app.core.security import require_admin
from app.schemas.common import CommonResponse
from app.schemas.user import UserCreateRequest, UserListResponse, UserResponse, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "",
    summary="사용자 등록",
    description="새 사용자를 등록합니다.",
    response_model=CommonResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_user(request: UserCreateRequest, service: UserService = Depends(get_user_service)):
    user = service.create_user(request)
    return CommonResponse(success=True, message="사용자가 등록되었습니다.", data=UserResponse.model_validate(user))


@router.get(
    "",
    summary="사용자 목록 조회",
    description="등록된 사용자 목록을 조회합니다.",
    response_model=CommonResponse[UserListResponse],
    status_code=status.HTTP_200_OK,
)
def list_users(
    service: UserService = Depends(get_user_service),
    _: object = Depends(require_admin),
):
    users = service.list_users()
    data = UserListResponse(items=[UserResponse.model_validate(item) for item in users], total=len(users))
    return CommonResponse(success=True, message="사용자 목록입니다.", data=data)


@router.get(
    "/{user_id}",
    summary="사용자 단건 조회",
    description="사용자 상세 정보를 조회합니다.",
    response_model=CommonResponse[UserResponse],
    status_code=status.HTTP_200_OK,
)
def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    _: object = Depends(require_admin),
):
    user = service.get_user(user_id)
    return CommonResponse(success=True, message="사용자 정보입니다.", data=UserResponse.model_validate(user))


@router.patch(
    "/{user_id}",
    summary="사용자 수정",
    description="사용자 정보를 수정합니다.",
    response_model=CommonResponse[UserResponse],
    status_code=status.HTTP_200_OK,
)
def update_user(
    user_id: int,
    request: UserUpdateRequest,
    service: UserService = Depends(get_user_service),
    _: object = Depends(require_admin),
):
    user = service.update_user(user_id, request)
    return CommonResponse(success=True, message="사용자 정보가 수정되었습니다.", data=UserResponse.model_validate(user))
