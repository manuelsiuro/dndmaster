from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DW_", env_file=".env", extra="ignore")

    app_name: str = "DragonWeaver API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://dragonweaver:dragonweaver@127.0.0.1:5432/dragonweaver"
    memory_embedding_dimensions: int = 1536
    memory_auto_ingest_timeline: bool = True

    jwt_secret: str = Field(default="change-me-in-dev-only", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    cors_origins: list[str] = ["http://localhost:5173"]
    media_root: str = "./media"
    media_url_prefix: str = "/media"
    max_audio_upload_bytes: int = 8 * 1024 * 1024
    ollama_base_url: str = "http://127.0.0.1:11434"


@lru_cache
def get_settings() -> Settings:
    return Settings()
