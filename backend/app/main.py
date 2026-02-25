from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.db.init_db import init_db
from app.db.session import create_engine_and_sessionmaker
from app.services.session_event_broker import SessionEventBroker
from app.services.voice_signal_broker import VoiceSignalBroker


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine, session_maker = create_engine_and_sessionmaker(app_settings.database_url)
        app.state.engine = engine
        app.state.session_maker = session_maker
        app.state.settings = app_settings
        app.state.session_event_broker = SessionEventBroker()
        app.state.voice_signal_broker = VoiceSignalBroker()
        Path(app_settings.media_root).mkdir(parents=True, exist_ok=True)
        await init_db(engine)
        yield
        await engine.dispose()

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount(
        app_settings.media_url_prefix,
        StaticFiles(directory=app_settings.media_root, check_dir=False),
        name="media",
    )

    app.include_router(api_router, prefix=app_settings.api_v1_prefix)

    return app


app = create_app()
