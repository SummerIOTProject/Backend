from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.runtime import ensure_upload_storage_ready
from app.core.database import get_db
from app.models import *  # noqa: F401,F403
from app.schemas.common import ErrorDetailSchema, ErrorResponse, HealthResponse, HealthStatusData


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_upload_storage_ready()
    yield


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health/live", response_model=HealthResponse, tags=["Health"])
def liveness_check():
    return HealthResponse(message="서버 프로세스가 정상 작동 중입니다.", data=HealthStatusData(status="UP"))


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.get("/health/ready", response_model=HealthResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        ensure_upload_storage_ready()
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                success=False,
                message="데이터베이스에 연결할 수 없습니다.",
                error=ErrorDetailSchema(code="DATABASE_UNAVAILABLE", detail=None),
            ).model_dump(),
        )
    except RuntimeError:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                success=False,
                message="업로드 저장소를 사용할 수 없습니다.",
                error=ErrorDetailSchema(code="STORAGE_UNAVAILABLE", detail=None),
            ).model_dump(),
        )
    return HealthResponse(
        message="서버가 정상 작동 중입니다.",
        data=HealthStatusData(status="UP", database="UP", storage="UP"),
    )


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            message=exc.message,
            error=ErrorDetailSchema(code=exc.code, detail=exc.detail),
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            success=False,
            message="요청 처리에 실패했습니다.",
            error=ErrorDetailSchema(code="VALIDATION_ERROR", detail=str(exc)),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            message="요청 처리에 실패했습니다.",
            error=ErrorDetailSchema(code="INTERNAL_SERVER_ERROR", detail=type(exc).__name__),
        ).model_dump(),
    )
