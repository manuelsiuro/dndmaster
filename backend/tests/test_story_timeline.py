def _register(client, email: str) -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SuperSecret123"},
    )
    assert resp.status_code == 201
    return resp.json()


def _create_story(client, headers: dict[str, str], title: str) -> dict:
    resp = client.post(
        "/api/v1/stories",
        json={"title": title, "description": "Story for timeline tests"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


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
    return start_resp.json()


def test_story_and_timeline_flow_with_consent(client):
    auth = _register(client, "gm@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    story_resp = client.post(
        "/api/v1/stories",
        json={"title": "The Sunken Keep", "description": "Session zero"},
        headers=headers,
    )
    assert story_resp.status_code == 201
    story = story_resp.json()

    consent_resp = client.post(
        "/api/v1/timeline/consents",
        json={"story_id": story["id"], "consent_scope": "session_recording"},
        headers=headers,
    )
    assert consent_resp.status_code == 201

    event_resp = client.post(
        "/api/v1/timeline/events",
        json={
            "story_id": story["id"],
            "event_type": "gm_prompt",
            "text_content": "You enter a dark hallway.",
            "language": "en",
            "audio": {
                "audio_ref": "s3://bucket/voice-001.webm",
                "duration_ms": 2400,
                "codec": "audio/webm;codecs=opus",
            },
            "transcript_segments": [
                {
                    "content": "You enter a dark hallway.",
                    "language": "en",
                    "confidence": 0.98,
                }
            ],
        },
        headers=headers,
    )
    assert event_resp.status_code == 201
    event = event_resp.json()
    assert event["recording"] is not None
    assert len(event["transcript_segments"]) == 1

    list_resp = client.get(
        f"/api/v1/timeline/events?story_id={story['id']}&limit=10&offset=0",
        headers=headers,
    )
    assert list_resp.status_code == 200
    events = list_resp.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "gm_prompt"


def test_timeline_event_with_audio_requires_consent(client):
    auth = _register(client, "gm2@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    story = client.post(
        "/api/v1/stories",
        json={"title": "No Consent Story"},
        headers=headers,
    ).json()

    event_resp = client.post(
        "/api/v1/timeline/events",
        json={
            "story_id": story["id"],
            "event_type": "player_action",
            "audio": {
                "audio_ref": "s3://bucket/voice-002.webm",
                "duration_ms": 1000,
                "codec": "audio/webm;codecs=opus",
            },
        },
        headers=headers,
    )

    assert event_resp.status_code == 400


def test_session_player_can_read_and_create_story_timeline(client):
    host_auth = _register(client, "timeline-host@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Session Timeline Story")
    started = _create_and_start_session(client, host_headers, story["id"])

    player_auth = _register(client, "timeline-player@example.com")
    player_headers = {"Authorization": f"Bearer {player_auth['access_token']}"}
    join_resp = client.post(
        "/api/v1/sessions/join",
        json={
            "join_token": started["join_token"],
            "device_fingerprint": "timeline-player-device",
        },
        headers=player_headers,
    )
    assert join_resp.status_code == 200

    host_event_resp = client.post(
        "/api/v1/timeline/events",
        json={
            "story_id": story["id"],
            "event_type": "gm_prompt",
            "text_content": "A stone gate opens with a roar.",
            "language": "en",
        },
        headers=host_headers,
    )
    assert host_event_resp.status_code == 201

    player_list_resp = client.get(
        f"/api/v1/timeline/events?story_id={story['id']}&limit=10&offset=0",
        headers=player_headers,
    )
    assert player_list_resp.status_code == 200
    player_events = player_list_resp.json()
    assert len(player_events) == 1
    assert player_events[0]["text_content"] == "A stone gate opens with a roar."

    player_event_resp = client.post(
        "/api/v1/timeline/events",
        json={
            "story_id": story["id"],
            "event_type": "player_action",
            "text_content": "I inspect the glyphs on the gate.",
            "language": "en",
        },
        headers=player_headers,
    )
    assert player_event_resp.status_code == 201

    outsider_auth = _register(client, "timeline-outsider@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_auth['access_token']}"}
    outsider_list_resp = client.get(
        f"/api/v1/timeline/events?story_id={story['id']}&limit=10&offset=0",
        headers=outsider_headers,
    )
    assert outsider_list_resp.status_code == 404
