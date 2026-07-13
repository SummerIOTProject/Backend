from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.allergen_seed import ALLERGEN_SEEDS
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.exceptions import AppException
from app.models.allergen import Allergen
from app.models import *  # noqa: F401,F403
from app.schemas.common import ErrorDetailSchema, ErrorResponse, HealthResponse


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    seed_allergens(SessionLocal())
    yield


def seed_allergens(db: Session) -> None:
    try:
        existing = {item.code: item for item in db.query(Allergen).all()}
        legacy_map = {"EGG": "EGGS", "SULFITE": "SULFITES"}
        for old_code, new_code in legacy_map.items():
            if old_code in existing and new_code not in existing:
                existing[old_code].code = new_code
        db.flush()
        existing = {item.code: item for item in db.query(Allergen).all()}
        for code, name_ko, display_number in ALLERGEN_SEEDS:
            allergen = existing.get(code)
            if allergen:
                allergen.name_ko = name_ko
                allergen.display_number = display_number
                allergen.is_active = True
            else:
                db.add(Allergen(code=code, name_ko=name_ko, display_number=display_number, is_active=True))
        db.commit()
    finally:
        db.close()


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    return HealthResponse(status="ok")


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
