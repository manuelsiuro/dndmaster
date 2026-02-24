import json
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import urlopen

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.db.models import UserSettings
from app.schemas.settings import OllamaModelsResponse, UserSettingsRead, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


async def _get_or_create_user_settings(current_user: CurrentUser, db: DBSession) -> UserSettings:
    settings = await db.scalar(select(UserSettings).where(UserSettings.user_id == current_user.id))
    if settings is not None:
        return settings

    settings = UserSettings(user_id=current_user.id)
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


def _fetch_ollama_models(base_url: str) -> list[str]:
    tags_url = urljoin(base_url.rstrip("/") + "/", "api/tags")
    try:
        with urlopen(tags_url, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, ValueError):
        return []

    seen: set[str] = set()
    models: list[str] = []
    for item in payload.get("models", []):
        name = str(item.get("name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        models.append(name)
    return sorted(models)


@router.get("/me", response_model=UserSettingsRead)
async def get_my_settings(current_user: CurrentUser, db: DBSession) -> UserSettingsRead:
    settings = await _get_or_create_user_settings(current_user, db)
    return UserSettingsRead.model_validate(settings)


@router.put("/me", response_model=UserSettingsRead)
async def update_my_settings(
    payload: UserSettingsUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> UserSettingsRead:
    settings = await _get_or_create_user_settings(current_user, db)
    patch = payload.model_dump(exclude_unset=True)
    for key, value in patch.items():
        setattr(settings, key, value)
    await db.commit()
    await db.refresh(settings)
    return UserSettingsRead.model_validate(settings)


@router.get("/ollama/models", response_model=OllamaModelsResponse)
async def list_ollama_models(request: Request, current_user: CurrentUser) -> OllamaModelsResponse:
    # Current user dependency enforces authenticated access.
    _ = current_user
    base_url = request.app.state.settings.ollama_base_url
    models = _fetch_ollama_models(base_url)
    return OllamaModelsResponse(available=len(models) > 0, models=models)
