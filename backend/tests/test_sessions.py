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
        json={"title": title, "description": "Story for session tests"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_and_start_session(
    client,
    host_headers: dict[str, str],
    story_id: str,
    *,
    max_players: int = 4,
) -> tuple[dict, dict]:
    create_response = client.post(
        "/api/v1/sessions",
        json={"story_id": story_id, "max_players": max_players},
        headers=host_headers,
    )
    assert create_response.status_code == 201
    session = create_response.json()

    start_response = client.post(
        f"/api/v1/sessions/{session['id']}/start",
        json={"token_ttl_minutes": 15},
        headers=host_headers,
    )
    assert start_response.status_code == 200
    started = start_response.json()
    return session, started


def test_host_create_start_and_player_join_with_token(client):
    host_auth = _register(client, "host@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Moonfall Archive")

    created_session, started = _create_and_start_session(client, host_headers, story["id"])
    assert created_session["status"] == "lobby"
    assert started["session"]["status"] == "active"

    join_token = started["join_token"]
    assert join_token

    player_auth = _register(client, "player01@example.com")
    player_headers = {"Authorization": f"Bearer {player_auth['access_token']}"}

    join_response = client.post(
        "/api/v1/sessions/join",
        json={"join_token": join_token, "device_fingerprint": "mobile-player-01"},
        headers=player_headers,
    )
    assert join_response.status_code == 200
    joined = join_response.json()
    assert joined["id"] == created_session["id"]
    assert len(joined["players"]) == 2
    assert any(item["user_email"] == "player01@example.com" for item in joined["players"])

    get_response = client.get(f"/api/v1/sessions/{created_session['id']}", headers=player_headers)
    assert get_response.status_code == 200


def test_session_enforces_single_active_device_per_player(client):
    host_auth = _register(client, "host-device@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Silent Cathedral")
    _, started = _create_and_start_session(client, host_headers, story["id"])

    player_auth = _register(client, "player-device@example.com")
    player_headers = {"Authorization": f"Bearer {player_auth['access_token']}"}
    payload = {"join_token": started["join_token"], "device_fingerprint": "device-a"}
    first_join_response = client.post(
        "/api/v1/sessions/join",
        json=payload,
        headers=player_headers,
    )
    assert first_join_response.status_code == 200

    repeat_join_response = client.post(
        "/api/v1/sessions/join",
        json=payload,
        headers=player_headers,
    )
    assert repeat_join_response.status_code == 200

    second_device_response = client.post(
        "/api/v1/sessions/join",
        json={"join_token": started["join_token"], "device_fingerprint": "device-b"},
        headers=player_headers,
    )
    assert second_device_response.status_code == 409


def test_session_enforces_mvp_player_cap_excluding_host(client):
    host_auth = _register(client, "host-cap@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Sunken Obelisk")
    _, started = _create_and_start_session(client, host_headers, story["id"], max_players=4)

    join_token = started["join_token"]
    for index in range(1, 5):
        player_auth = _register(client, f"cap-player-{index}@example.com")
        player_headers = {"Authorization": f"Bearer {player_auth['access_token']}"}
        response = client.post(
            "/api/v1/sessions/join",
            json={
                "join_token": join_token,
                "device_fingerprint": f"cap-device-{index}",
            },
            headers=player_headers,
        )
        assert response.status_code == 200

    overflow_auth = _register(client, "cap-player-overflow@example.com")
    overflow_headers = {"Authorization": f"Bearer {overflow_auth['access_token']}"}
    overflow_response = client.post(
        "/api/v1/sessions/join",
        json={"join_token": join_token, "device_fingerprint": "cap-device-overflow"},
        headers=overflow_headers,
    )
    assert overflow_response.status_code == 409
    assert "full" in overflow_response.text.lower()


def test_host_can_kick_player_and_player_cannot_rejoin(client):
    host_auth = _register(client, "host-kick@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "The Last Beacon")
    session, started = _create_and_start_session(client, host_headers, story["id"])

    player_auth = _register(client, "player-kick@example.com")
    player_headers = {"Authorization": f"Bearer {player_auth['access_token']}"}
    assert client.post(
        "/api/v1/sessions/join",
        json={"join_token": started["join_token"], "device_fingerprint": "kick-device"},
        headers=player_headers,
    ).status_code == 200

    kick_response = client.post(
        f"/api/v1/sessions/{session['id']}/kick",
        json={"user_id": player_auth["user"]["id"]},
        headers=host_headers,
    )
    assert kick_response.status_code == 200

    after_kick_get = client.get(f"/api/v1/sessions/{session['id']}", headers=player_headers)
    assert after_kick_get.status_code == 404

    rejoin_response = client.post(
        "/api/v1/sessions/join",
        json={"join_token": started["join_token"], "device_fingerprint": "kick-device"},
        headers=player_headers,
    )
    assert rejoin_response.status_code == 403
