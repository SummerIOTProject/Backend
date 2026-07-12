from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_auth_service
from app.core.security import require_active_user
from app.schemas.auth import ChangePasswordRequest, CurrentUserResponse, LoginRequest, SignUpRequest, TokenResponse
from app.schemas.common import CommonResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def _to_current_user_response(user) -> CurrentUserResponse:
    return CurrentUserResponse(
        user_id=user.id,
        name=user.name,
        student_number=user.student_number,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.post(
    "/signup",
    summary="학생 회원가입",
    description="이름, 학번, 이메일, 비밀번호로 학생 계정을 생성합니다.",
    response_model=CommonResponse[CurrentUserResponse],
    status_code=status.HTTP_201_CREATED,
)
def signup(request: SignUpRequest, service: AuthService = Depends(get_auth_service)):
    user = service.signup(request)
    return CommonResponse(success=True, message="회원가입이 완료되었습니다.", data=_to_current_user_response(user))


@router.post(
    "/login",
    summary="로그인",
    description="이메일과 비밀번호를 검증하고 Access Token을 발급합니다.",
    response_model=CommonResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
def login(request: LoginRequest, service: AuthService = Depends(get_auth_service)):
    token = service.login(request)
    return CommonResponse(success=True, message="로그인되었습니다.", data=token)


@router.post(
    "/refresh",
    summary="Access Token 재발급",
    description="현재 인증된 사용자의 Access Token을 재발급합니다.",
    response_model=CommonResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
def refresh_token(service: AuthService = Depends(get_auth_service), current_user=Depends(require_active_user)):
    token = service.refresh_access_token(current_user.id, current_user.role)
    return CommonResponse(success=True, message="Access Token이 재발급되었습니다.", data=token)


@router.post(
    "/logout",
    summary="로그아웃",
    description="현재 Access Token 기반 세션을 종료합니다.",
    response_model=CommonResponse[None],
    status_code=status.HTTP_200_OK,
)
def logout(_: object = Depends(require_active_user)):
    return CommonResponse(
        success=True,
        message="로그아웃되었습니다. 현재 구현은 Access Token 단독 구조이므로 클라이언트에서 토큰을 삭제해야 합니다.",
        data=None,
    )


@router.get(
    "/me",
    summary="현재 로그인 사용자 조회",
    description="JWT 기준 현재 로그인한 사용자 정보를 반환합니다.",
    response_model=CommonResponse[CurrentUserResponse],
    status_code=status.HTTP_200_OK,
)
def get_me(current_user=Depends(require_active_user)):
    return CommonResponse(success=True, message="현재 사용자 정보입니다.", data=_to_current_user_response(current_user))


@router.patch(
    "/password",
    summary="비밀번호 변경",
    description="현재 로그인한 사용자의 비밀번호를 변경합니다.",
    response_model=CommonResponse[None],
    status_code=status.HTTP_200_OK,
)
def change_password(
    request: ChangePasswordRequest,
    service: AuthService = Depends(get_auth_service),
    current_user=Depends(require_active_user),
):
    service.change_password(current_user.id, request)
    return CommonResponse(success=True, message="비밀번호가 변경되었습니다.", data=None)
