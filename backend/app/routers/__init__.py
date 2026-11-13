from .auth import router as auth_router
from .materials import router as materials_router
from .admin import router as admin_router
from .reviews import router as reviews_router
from .bookmarks import router as bookmarks_router
from .categories import router as categories_router
from .scanning_booth import router as scanning_booth_router
from .classifier import router as classifier_router
from .quality import router as quality_router
from .summaries import router as summaries_router
from .search import router as search_router
from .similarity import router as similarity_router
from .chat import router as chat_router
from .study_buddy import router as study_buddy_router
from .guardrails import router as guardrails_router
from .recognition import router as recognition_router

__all__ = [
    "auth_router",
    "materials_router",
    "admin_router",
    "reviews_router",
    "bookmarks_router",
    "categories_router",
    "scanning_booth_router",
    "classifier_router",
    "quality_router",
    "summaries_router",
    "search_router",
    "similarity_router",
    "chat_router",
    "study_buddy_router",
    "guardrails_router",
    "recognition_router",
]
