from dataclasses import dataclass


@dataclass
class ErrorDetail:
    code: str
    detail: str | None = None


class AppException(Exception):
    def __init__(self, message: str, code: str, status_code: int, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail


class NotFoundException(AppException):
    def __init__(self, message: str, code: str, detail: str | None = None) -> None:
        super().__init__(message=message, code=code, status_code=404, detail=detail)


class ConflictException(AppException):
    def __init__(self, message: str, code: str, detail: str | None = None) -> None:
        super().__init__(message=message, code=code, status_code=409, detail=detail)


class BadRequestException(AppException):
    def __init__(self, message: str, code: str, detail: str | None = None) -> None:
        super().__init__(message=message, code=code, status_code=400, detail=detail)


class UnauthorizedException(AppException):
    def __init__(self, message: str, code: str, detail: str | None = None) -> None:
        super().__init__(message=message, code=code, status_code=401, detail=detail)


class ForbiddenException(AppException):
    def __init__(self, message: str, code: str, detail: str | None = None) -> None:
        super().__init__(message=message, code=code, status_code=403, detail=detail)
