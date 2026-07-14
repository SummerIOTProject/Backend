from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_menu_service
from app.core.security import require_admin
from app.schemas.common import CommonResponse
from app.schemas.menu import MenuCreateRequest, MenuListResponse, MenuResponse, MenuUpdateRequest
from app.services.menu_service import MenuService

router = APIRouter(tags=["Menus"])


def _menu_response(menu) -> MenuResponse:
    return MenuResponse(
        id=menu.id,
        name=menu.name,
        standard_serving_g=menu.standard_serving_g,
        calories_per_100g=menu.calories_per_100g,
        carbohydrate_per_100g=menu.carbohydrate_per_100g,
        protein_per_100g=menu.protein_per_100g,
        fat_per_100g=menu.fat_per_100g,
        is_active=menu.is_active,
        created_at=menu.created_at,
        updated_at=menu.updated_at,
        ingredients=[link.ingredient.name for link in menu.ingredients],
        allergen_codes=[link.allergen.code for link in menu.allergens],
    )


@router.post("/admin/menus", response_model=CommonResponse[MenuResponse], status_code=status.HTTP_201_CREATED)
def create_menu(request: MenuCreateRequest, _: object = Depends(require_admin), service: MenuService = Depends(get_menu_service)):
    return CommonResponse(message="메뉴가 등록되었습니다.", data=_menu_response(service.create_menu(request)))


@router.get("/menus", response_model=CommonResponse[MenuListResponse])
def list_menus(include_inactive: bool = Query(default=False), service: MenuService = Depends(get_menu_service)):
    items = service.list_menus(include_inactive=include_inactive)
    return CommonResponse(message="메뉴 목록입니다.", data=MenuListResponse(items=[_menu_response(item) for item in items], total=len(items)))


@router.get("/menus/{menu_id}", response_model=CommonResponse[MenuResponse])
def get_menu(menu_id: int, service: MenuService = Depends(get_menu_service)):
    return CommonResponse(message="메뉴 상세입니다.", data=_menu_response(service.get_menu(menu_id)))


@router.patch("/admin/menus/{menu_id}", response_model=CommonResponse[MenuResponse])
def update_menu(menu_id: int, request: MenuUpdateRequest, _: object = Depends(require_admin), service: MenuService = Depends(get_menu_service)):
    return CommonResponse(message="메뉴가 수정되었습니다.", data=_menu_response(service.update_menu(menu_id, request)))


@router.delete("/admin/menus/{menu_id}", response_model=CommonResponse[None])
def delete_menu(menu_id: int, _: object = Depends(require_admin), service: MenuService = Depends(get_menu_service)):
    service.delete_menu(menu_id)
    return CommonResponse(message="메뉴가 비활성화되었습니다.", data=None)
