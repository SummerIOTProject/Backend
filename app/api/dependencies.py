from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.analysis_service import AnalysisService
from app.services.auth_service import AuthService
from app.services.image_service import ImageService
from app.services.meal_record_service import MealRecordService
from app.services.meal_service import MealService
from app.services.recommendation_service import RecommendationService
from app.services.rfid_service import RfidService
from app.services.user_service import UserService


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_rfid_service(db: Session = Depends(get_db)) -> RfidService:
    return RfidService(db)


def get_meal_service(db: Session = Depends(get_db)) -> MealService:
    return MealService(db)


def get_meal_record_service(db: Session = Depends(get_db)) -> MealRecordService:
    return MealRecordService(db)


def get_image_service(db: Session = Depends(get_db)) -> ImageService:
    return ImageService(db)


def get_analysis_service(db: Session = Depends(get_db)) -> AnalysisService:
    return AnalysisService(db)


def get_recommendation_service(db: Session = Depends(get_db)) -> RecommendationService:
    return RecommendationService(db)
