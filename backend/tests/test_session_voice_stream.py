import pytest
from starlette.websockets import WebSocketDisconnect


def _register(client, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SuperSecret123"},
    )
    assert response.status_code == 201
    return response.json()


def _create_story(client, headers: dict[str, str], title: str) -> dict:
    response = client.post(
        "/api/v1/stories",
        json={"title": title, "description": "Story for voice stream tests"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_and_start_session(client, host_headers: dict[str, str], story_id: str) -> dict:
    create_resp = client.post(
        "/api/v1/sessions",
        json={"story_id": story_id, "max_players": 4},
        headers=host_headers,
    )
    assert create_resp.status_code == 201
    session = create_resp.json()

    start_resp = client.post(
        f"/api/v1/sessions/{session['id']}/start",
        json={"token_ttl_minutes": 15},
        headers=host_headers,
    )
    assert start_resp.status_code == 200
    started = start_resp.json()
    return {"session": session, "started": started}


def test_voice_stream_relays_signals_and_presence(client):
    host_auth = _register(client, "voice-host@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Voice Session Story")
    session_bundle = _create_and_start_session(client, host_headers, story["id"])

    player_auth = _register(client, "voice-player@example.com")
    player_headers = {"Authorization": f"Bearer {player_auth['access_token']}"}
    join_resp = client.post(
        "/api/v1/sessions/join",
        json={
            "join_token": session_bundle["started"]["join_token"],
            "device_fingerprint": "voice-player-device",
        },
        headers=player_headers,
    )
    assert join_resp.status_code == 200

    session_id = session_bundle["session"]["id"]
    host_token = host_auth["access_token"]
    player_token = player_auth["access_token"]
    player_id = player_auth["user"]["id"]
    host_id = host_auth["user"]["id"]

    with client.websocket_connect(
        f"/api/v1/sessions/{session_id}/voice/stream?access_token={host_token}"
    ) as host_ws:
        host_snapshot = host_ws.receive_json()
        assert host_snapshot["type"] == "voice_snapshot"
        assert host_snapshot["self_user_id"] == host_id
        assert host_snapshot["peers"] == [
            {
                "user_id": player_id,
                "user_email": "voice-player@example.com",
                "role": "player",
            }
        ]

        with client.websocket_connect(
            f"/api/v1/sessions/{session_id}/voice/stream?access_token={player_token}"
        ) as player_ws:
            player_snapshot = player_ws.receive_json()
            assert player_snapshot["type"] == "voice_snapshot"
            assert player_snapshot["self_user_id"] == player_id
            assert player_snapshot["peers"] == [
                {
                    "user_id": host_id,
                    "user_email": "voice-host@example.com",
                    "role": "host",
                }
            ]

            host_joined = host_ws.receive_json()
            assert host_joined["type"] == "peer_joined"
            assert host_joined["user_id"] == player_id

            offer_payload = {"type": "offer", "sdp": "fake-offer-sdp"}
            host_ws.send_json(
                {
                    "type": "signal",
                    "signal_type": "offer",
                    "target_user_id": player_id,
                    "payload": offer_payload,
                }
            )

            player_signal = player_ws.receive_json()
            assert player_signal["type"] == "signal"
            assert player_signal["from_user_id"] == host_id
            assert player_signal["signal_type"] == "offer"
            assert player_signal["payload"] == offer_payload

        host_left = host_ws.receive_json()
        assert host_left["type"] == "peer_left"
        assert host_left["user_id"] == player_id


def test_voice_stream_denies_outsider(client):
    host_auth = _register(client, "voice-owner@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Private Voice Story")
    session_bundle = _create_and_start_session(client, host_headers, story["id"])

    outsider_auth = _register(client, "voice-outsider@example.com")
    outsider_token = outsider_auth["access_token"]
    session_id = session_bundle["session"]["id"]

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            f"/api/v1/sessions/{session_id}/voice/stream?access_token={outsider_token}"
        ):
            pass

    assert exc_info.value.code == 4404
