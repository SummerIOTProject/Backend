from enum import Enum


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"


class MealType(str, Enum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"


class MealRecordStatus(str, Enum):
    CREATED = "CREATED"
    BEFORE_IMAGE_UPLOADED = "BEFORE_IMAGE_UPLOADED"
    IMAGES_UPLOADED = "IMAGES_UPLOADED"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImageType(str, Enum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"


class ConsumptionLevel(str, Enum):
    NONE = "NONE"
    LITTLE = "LITTLE"
    HALF = "HALF"
    MOST = "MOST"
    ALL = "ALL"


class RecommendationLevel(str, Enum):
    LESS = "LESS"
    NORMAL = "NORMAL"


class AnalysisType(str, Enum):
    MOCK = "MOCK"
    OPENAI_VLM = "OPENAI_VLM"
