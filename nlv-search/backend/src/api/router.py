from fastapi import APIRouter
from src.api.auth.router import router as auth_router
from src.api.conversational_search.router import router as conversational_search_router
from src.api.health.router import router as health_router
from src.api.media.router import router as media_router

api_router = APIRouter()

api_router.include_router(auth_router)

api_router.include_router(health_router)

api_router.include_router(media_router)

api_router.include_router(conversational_search_router)
