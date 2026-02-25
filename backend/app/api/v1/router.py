from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    health,
    memory,
    orchestration,
    progression,
    saves,
    sessions,
    settings,
    stories,
    timeline,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(stories.router)
api_router.include_router(progression.router)
api_router.include_router(memory.router)
api_router.include_router(orchestration.router)
api_router.include_router(saves.router)
api_router.include_router(sessions.router)
api_router.include_router(timeline.router)
api_router.include_router(settings.router)
