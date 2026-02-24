import asyncio
import hashlib
import json
import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.db.models import (
    GameSession,
    JoinToken,
    SessionDeviceBinding,
    SessionParticipantRole,
    SessionPlayer,
    SessionStatus,
    Story,
)
from app.schemas.session import (
    JoinSessionRequest,
    KickPlayerRequest,
    SessionCreateRequest,
    SessionPlayerRead,
    SessionRead,
    SessionStartRequest,
    SessionStartResponse,
)
from app.services.session_event_broker import SessionEventBroker

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _hash_join_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _build_join_url(request: Request, join_token: str) -> str:
    settings = request.app.state.settings
    base_origin = settings.cors_origins[0] if settings.cors_origins else str(request.base_url)
    return f"{base_origin.rstrip('/')}/?joinToken={quote(join_token, safe='')}"


def _active_join_token_expires_at(session: GameSession, now: datetime) -> datetime | None:
    active_expiries = [
        _as_utc(item.expires_at)
        for item in session.join_tokens
        if item.revoked_at is None and _as_utc(item.expires_at) > now
    ]
    if not active_expiries:
        return None
    return max(active_expiries)


def _map_session(session: GameSession) -> SessionRead:
    now = datetime.now(UTC)
    active_players = [item for item in session.players if item.kicked_at is None]
    ordered_players = sorted(
        active_players,
        key=lambda item: (
            0 if item.role == SessionParticipantRole.host else 1,
            item.joined_at,
        ),
    )

    players = [
        SessionPlayerRead(
            user_id=item.user_id,
            user_email=item.user.email,
            role=item.role,
            joined_at=item.joined_at,
        )
        for item in ordered_players
    ]

    return SessionRead(
        id=session.id,
        story_id=session.story_id,
        host_user_id=session.host_user_id,
        status=session.status,
        max_players=session.max_players,
        created_at=session.created_at,
        started_at=session.started_at,
        ended_at=session.ended_at,
        active_join_token_expires_at=_active_join_token_expires_at(session, now),
        players=players,
    )


def _format_sse_event(event_name: str, payload: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


async def _publish_session_event(
    request: Request,
    session: GameSession,
    *,
    change_type: str,
) -> None:
    broker: SessionEventBroker = request.app.state.session_event_broker
    await broker.publish(
        session.id,
        {
            "change_type": change_type,
            "session": _map_session(session).model_dump(mode="json"),
        },
    )


def _session_select(session_id: str):
    return (
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(
            selectinload(GameSession.players).selectinload(SessionPlayer.user),
            selectinload(GameSession.join_tokens),
        )
    )


async def _load_session(session_id: str, db: DBSession) -> GameSession | None:
    return await db.scalar(
        _session_select(session_id).execution_options(populate_existing=True)
    )


async def _assert_story_owner(story_id: str, current_user: CurrentUser, db: DBSession) -> Story:
    story = await db.scalar(
        select(Story).where(Story.id == story_id, Story.owner_user_id == current_user.id)
    )
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    return story


def _session_has_access(session: GameSession, user_id: str) -> bool:
    if session.host_user_id == user_id:
        return True
    return any(item.user_id == user_id and item.kicked_at is None for item in session.players)


async def _assert_session_access(
    session_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> GameSession:
    session = await _load_session(session_id, db)
    if session is None or not _session_has_access(session, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def _assert_session_host(
    session_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> GameSession:
    session = await _load_session(session_id, db)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.host_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Host access required")
    return session


async def _create_join_token(
    session_id: str,
    created_by_user_id: str,
    ttl_minutes: int,
    db: DBSession,
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=ttl_minutes)
    raw_token = secrets.token_urlsafe(32)
    token = JoinToken(
        session_id=session_id,
        token_hash=_hash_join_token(raw_token),
        created_by_user_id=created_by_user_id,
        expires_at=expires_at,
    )
    db.add(token)
    return raw_token, expires_at


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreateRequest,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> SessionRead:
    await _assert_story_owner(payload.story_id, current_user, db)

    existing_open_session = await db.scalar(
        select(GameSession).where(
            GameSession.story_id == payload.story_id,
            GameSession.host_user_id == current_user.id,
            GameSession.status.in_([SessionStatus.lobby, SessionStatus.active]),
        )
    )
    if existing_open_session is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An open session already exists for this story",
        )

    session = GameSession(
        story_id=payload.story_id,
        host_user_id=current_user.id,
        max_players=payload.max_players,
    )
    host_player = SessionPlayer(
        session=session,
        user_id=current_user.id,
        role=SessionParticipantRole.host,
    )
    db.add_all([session, host_player])
    await db.commit()

    loaded = await _load_session(session.id, db)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session not found",
        )

    await _publish_session_event(request, loaded, change_type="session_created")

    return _map_session(loaded)


@router.get("", response_model=list[SessionRead])
async def list_sessions(
    current_user: CurrentUser,
    db: DBSession,
    story_id: str | None = Query(default=None),
) -> list[SessionRead]:
    stmt = (
        select(GameSession)
        .outerjoin(SessionPlayer, SessionPlayer.session_id == GameSession.id)
        .where(
            or_(
                GameSession.host_user_id == current_user.id,
                (
                    (SessionPlayer.user_id == current_user.id)
                    & SessionPlayer.kicked_at.is_(None)
                ),
            )
        )
        .options(
            selectinload(GameSession.players).selectinload(SessionPlayer.user),
            selectinload(GameSession.join_tokens),
        )
        .order_by(GameSession.created_at.desc())
        .distinct()
    )
    if story_id is not None:
        stmt = stmt.where(GameSession.story_id == story_id)

    sessions = await db.scalars(stmt)
    return [_map_session(item) for item in sessions.all()]


@router.get("/{session_id}", response_model=SessionRead)
async def get_session(
    session_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> SessionRead:
    session = await _assert_session_access(session_id, current_user, db)
    return _map_session(session)


@router.get("/{session_id}/stream")
async def stream_session(
    session_id: str,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> StreamingResponse:
    session = await _assert_session_access(session_id, current_user, db)
    broker: SessionEventBroker = request.app.state.session_event_broker

    initial_payload = {
        "change_type": "snapshot",
        "session": _map_session(session).model_dump(mode="json"),
    }

    async def stream() -> AsyncIterator[str]:
        yield _format_sse_event("session_snapshot", initial_payload)
        async with broker.subscribe(session_id) as queue:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=20)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield _format_sse_event("session_updated", payload)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{session_id}/start", response_model=SessionStartResponse)
async def start_session(
    session_id: str,
    payload: SessionStartRequest,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> SessionStartResponse:
    session = await _assert_session_host(session_id, current_user, db)
    if session.status == SessionStatus.ended:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session already ended")
    if session.status == SessionStatus.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is already active",
        )

    now = datetime.now(UTC)
    session.status = SessionStatus.active
    session.started_at = now

    raw_token, expires_at = await _create_join_token(
        session_id=session.id,
        created_by_user_id=current_user.id,
        ttl_minutes=payload.token_ttl_minutes,
        db=db,
    )
    await db.commit()

    loaded = await _load_session(session.id, db)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session not found",
        )

    await _publish_session_event(request, loaded, change_type="session_started")

    return SessionStartResponse(
        session=_map_session(loaded),
        join_token=raw_token,
        join_url=_build_join_url(request, raw_token),
        expires_at=expires_at,
    )


@router.post("/{session_id}/join-token", response_model=SessionStartResponse)
async def rotate_join_token(
    session_id: str,
    payload: SessionStartRequest,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> SessionStartResponse:
    session = await _assert_session_host(session_id, current_user, db)
    if session.status != SessionStatus.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session must be active to rotate join token",
        )

    now = datetime.now(UTC)
    await db.execute(
        update(JoinToken)
        .where(JoinToken.session_id == session.id, JoinToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )

    raw_token, expires_at = await _create_join_token(
        session_id=session.id,
        created_by_user_id=current_user.id,
        ttl_minutes=payload.token_ttl_minutes,
        db=db,
    )
    await db.commit()

    loaded = await _load_session(session.id, db)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session not found",
        )

    await _publish_session_event(request, loaded, change_type="join_token_rotated")

    return SessionStartResponse(
        session=_map_session(loaded),
        join_token=raw_token,
        join_url=_build_join_url(request, raw_token),
        expires_at=expires_at,
    )


@router.post("/join", response_model=SessionRead)
async def join_session(
    payload: JoinSessionRequest,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> SessionRead:
    now = datetime.now(UTC)
    token_hash = _hash_join_token(payload.join_token)
    join_token = await db.scalar(
        select(JoinToken).where(
            JoinToken.token_hash == token_hash,
            JoinToken.revoked_at.is_(None),
            JoinToken.expires_at > now,
        )
    )
    if join_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Join token is invalid or expired",
        )

    session = await _load_session(join_token.session_id, db)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status != SessionStatus.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session is not active")

    membership = await db.scalar(
        select(SessionPlayer).where(
            SessionPlayer.session_id == session.id,
            SessionPlayer.user_id == current_user.id,
        )
    )
    if membership is not None and membership.kicked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You were removed from this session",
        )

    if membership is None:
        active_player_count = await db.scalar(
            select(func.count())
            .select_from(SessionPlayer)
            .where(
                SessionPlayer.session_id == session.id,
                SessionPlayer.role == SessionParticipantRole.player,
                SessionPlayer.kicked_at.is_(None),
            )
        )
        if (
            current_user.id != session.host_user_id
            and active_player_count is not None
            and active_player_count >= session.max_players
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is full")

        membership = SessionPlayer(
            session_id=session.id,
            user_id=current_user.id,
            role=(
                SessionParticipantRole.host
                if current_user.id == session.host_user_id
                else SessionParticipantRole.player
            ),
        )
        db.add(membership)

    binding = await db.scalar(
        select(SessionDeviceBinding).where(
            SessionDeviceBinding.session_id == session.id,
            SessionDeviceBinding.user_id == current_user.id,
        )
    )
    if binding is None:
        binding = SessionDeviceBinding(
            session_id=session.id,
            user_id=current_user.id,
            device_fingerprint=payload.device_fingerprint,
        )
        db.add(binding)
    elif binding.revoked_at is not None:
        binding.device_fingerprint = payload.device_fingerprint
        binding.bound_at = now
        binding.last_seen_at = now
        binding.revoked_at = None
    elif binding.device_fingerprint != payload.device_fingerprint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another device is already active for this player",
        )
    else:
        binding.last_seen_at = now

    await db.commit()

    loaded = await _load_session(session.id, db)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session not found",
        )

    await _publish_session_event(request, loaded, change_type="player_joined")

    return _map_session(loaded)


@router.post("/{session_id}/kick", response_model=SessionRead)
async def kick_player(
    session_id: str,
    payload: KickPlayerRequest,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> SessionRead:
    session = await _assert_session_host(session_id, current_user, db)
    if payload.user_id == session.host_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Host cannot be kicked")

    membership = await db.scalar(
        select(SessionPlayer).where(
            SessionPlayer.session_id == session.id,
            SessionPlayer.user_id == payload.user_id,
        )
    )
    if membership is None or membership.kicked_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    now = datetime.now(UTC)
    membership.kicked_at = now

    binding = await db.scalar(
        select(SessionDeviceBinding).where(
            SessionDeviceBinding.session_id == session.id,
            SessionDeviceBinding.user_id == payload.user_id,
            SessionDeviceBinding.revoked_at.is_(None),
        )
    )
    if binding is not None:
        binding.revoked_at = now

    await db.commit()

    loaded = await _load_session(session.id, db)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session not found",
        )

    await _publish_session_event(request, loaded, change_type="player_kicked")

    return _map_session(loaded)


@router.post("/{session_id}/end", response_model=SessionRead)
async def end_session(
    session_id: str,
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
) -> SessionRead:
    session = await _assert_session_host(session_id, current_user, db)
    if session.status != SessionStatus.ended:
        now = datetime.now(UTC)
        session.status = SessionStatus.ended
        session.ended_at = now
        await db.execute(
            update(JoinToken)
            .where(JoinToken.session_id == session.id, JoinToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()

    loaded = await _load_session(session.id, db)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session not found",
        )

    await _publish_session_event(request, loaded, change_type="session_ended")

    return _map_session(loaded)
