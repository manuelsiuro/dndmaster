def _register(client, email: str) -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SuperSecret123"},
    )
    assert resp.status_code == 201
    return resp.json()


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
