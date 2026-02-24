from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, stories, timeline

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(stories.router)
api_router.include_router(timeline.router)
