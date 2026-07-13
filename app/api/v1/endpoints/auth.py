from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_auth_service
from app.core.security import get_current_user
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LogoutRequest, RefreshTokenRequest, SignUpRequest, TokenPairResponse
from app.schemas.common import CommonResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=CommonResponse[UserResponse], status_code=status.HTTP_201_CREATED)
def signup(request: SignUpRequest, service: AuthService = Depends(get_auth_service)):
    user = service.signup(request)
    return CommonResponse(message="회원가입이 완료되었습니다.", data=UserResponse.model_validate(user))


@router.post("/login", response_model=CommonResponse[TokenPairResponse])
def login(request: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return CommonResponse(message="로그인되었습니다.", data=service.login(request))


@router.post("/refresh", response_model=CommonResponse[TokenPairResponse])
def refresh(request: RefreshTokenRequest, service: AuthService = Depends(get_auth_service)):
    return CommonResponse(message="토큰이 재발급되었습니다.", data=service.refresh(request))


@router.post("/logout", response_model=CommonResponse[None])
def logout(request: LogoutRequest, service: AuthService = Depends(get_auth_service)):
    service.logout(request)
    return CommonResponse(message="로그아웃되었습니다.", data=None)


@router.patch("/password", response_model=CommonResponse[None])
def change_password(request: ChangePasswordRequest, current_user=Depends(get_current_user), service: AuthService = Depends(get_auth_service)):
    service.change_password(current_user.id, request)
    return CommonResponse(message="비밀번호가 변경되었습니다.", data=None)
