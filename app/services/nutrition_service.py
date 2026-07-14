from app.models.menu import Menu


class NutritionService:
    @staticmethod
    def calculate(menu: Menu, consumed_ratio: float) -> dict[str, float | bool]:
        estimated_consumed_g = round(menu.standard_serving_g * consumed_ratio, 2)
        factor = estimated_consumed_g / 100
        return {
            "estimated_consumed_g": estimated_consumed_g,
            "calories_kcal": round(menu.calories_per_100g * factor, 2),
            "carbohydrate_g": round(menu.carbohydrate_per_100g * factor, 2),
            "protein_g": round(menu.protein_per_100g * factor, 2),
            "fat_g": round(menu.fat_per_100g * factor, 2),
            "is_estimated": True,
        }
