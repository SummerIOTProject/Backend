from pydantic import BaseModel, EmailStr, Field, field_validator


class SignUpRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    student_number: str = Field(min_length=1, max_length=30)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        has_upper = any(char.isupper() for char in value)
        has_lower = any(char.islower() for char in value)
        has_digit = any(char.isdigit() for char in value)
        if not (has_upper and has_lower and has_digit):
            raise ValueError("비밀번호는 영문 대문자, 소문자, 숫자를 모두 포함해야 합니다.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        has_upper = any(char.isupper() for char in value)
        has_lower = any(char.islower() for char in value)
        has_digit = any(char.isdigit() for char in value)
        if not (has_upper and has_lower and has_digit):
            raise ValueError("비밀번호는 영문 대문자, 소문자, 숫자를 모두 포함해야 합니다.")
        return value


class CurrentUserResponse(BaseModel):
    user_id: int
    name: str
    student_number: str
    email: EmailStr
    role: str
    is_active: bool
