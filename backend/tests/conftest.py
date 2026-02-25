import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "test.db"
    media_root = tmp_path / "media"
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{db_path}",
        jwt_secret="test-secret-key-1234567890",
        cors_origins=["*"],
        media_root=str(media_root),
        tts_provider_fallback_chain=["deterministic"],
    )
    app = create_app(settings)

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def postgres_client(tmp_path) -> Generator[TestClient, None, None]:
    database_url = os.getenv("TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("TEST_POSTGRES_URL is not set")

    media_root = tmp_path / "media-postgres"
    settings = Settings(
        environment="test",
        database_url=database_url,
        jwt_secret="test-secret-key-1234567890",
        cors_origins=["*"],
        media_root=str(media_root),
        tts_provider_fallback_chain=["deterministic"],
    )
    app = create_app(settings)

    with TestClient(app) as test_client:
        yield test_client
