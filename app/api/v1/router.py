from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, me, meal_analyses, meal_images, meal_records, meals, recommendations, rfid_cards, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(users.router)
api_router.include_router(rfid_cards.router)
api_router.include_router(meals.router)
api_router.include_router(meal_records.router)
api_router.include_router(meal_images.router)
api_router.include_router(meal_analyses.router)
api_router.include_router(recommendations.router)
api_router.include_router(admin.router)
