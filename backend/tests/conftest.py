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
    )
    app = create_app(settings)

    with TestClient(app) as test_client:
        yield test_client
