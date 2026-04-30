from fastapi import APIRouter
from src.api.embed.router import router as embed_router
from src.api.health.router import router as health_router
from src.api.llm.router import router as llm_router

api_router = APIRouter()

api_router.include_router(health_router)

api_router.include_router(embed_router)

api_router.include_router(llm_router)
