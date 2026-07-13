from fastapi import APIRouter

from app.api.v1.endpoints import admin, allergens, auth, device, me, meal_analyses, meal_images, meal_records, meals, menus

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(allergens.router)
api_router.include_router(menus.router)
api_router.include_router(meals.router)
api_router.include_router(meal_records.router)
api_router.include_router(meal_images.router)
api_router.include_router(meal_analyses.router)
api_router.include_router(device.router)
api_router.include_router(admin.router)
