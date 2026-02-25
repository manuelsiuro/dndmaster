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
        json={"title": title, "description": "Story for progression tests"},
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
    return {"session": session, "started": start_resp.json()}


def test_progression_awards_persist_across_stories(client):
    host_auth = _register(client, "progress-host@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    player_auth = _register(client, "progress-player@example.com")
    player_headers = {"Authorization": f"Bearer {player_auth['access_token']}"}

    first_story = _create_story(client, host_headers, "Progress Story One")
    first_bundle = _create_and_start_session(client, host_headers, first_story["id"])
    join_one = client.post(
        "/api/v1/sessions/join",
        json={
            "join_token": first_bundle["started"]["join_token"],
            "device_fingerprint": "progress-device-one",
        },
        headers=player_headers,
    )
    assert join_one.status_code == 200

    award_one = client.post(
        "/api/v1/progression/award",
        json={
            "story_id": first_story["id"],
            "user_id": player_auth["user"]["id"],
            "xp_delta": 350,
            "reason": "Solved the tomb puzzle",
        },
        headers=host_headers,
    )
    assert award_one.status_code == 201
    assert award_one.json()["progression"]["level"] == 2

    second_story = _create_story(client, host_headers, "Progress Story Two")
    second_bundle = _create_and_start_session(client, host_headers, second_story["id"])
    join_two = client.post(
        "/api/v1/sessions/join",
        json={
            "join_token": second_bundle["started"]["join_token"],
            "device_fingerprint": "progress-device-one",
        },
        headers=player_headers,
    )
    assert join_two.status_code == 200

    award_two = client.post(
        "/api/v1/progression/award",
        json={
            "story_id": second_story["id"],
            "user_id": player_auth["user"]["id"],
            "xp_delta": 700,
            "reason": "Defeated the boss",
        },
        headers=host_headers,
    )
    assert award_two.status_code == 201
    assert award_two.json()["progression"]["xp_total"] == 1050
    assert award_two.json()["progression"]["level"] == 3

    me_progression = client.get("/api/v1/progression/me", headers=player_headers)
    assert me_progression.status_code == 200
    me_payload = me_progression.json()
    assert me_payload["xp_total"] == 1050
    assert me_payload["level"] == 3
    assert len(me_payload["recent_entries"]) >= 2

    story_progression = client.get(
        f"/api/v1/progression/story/{first_story['id']}",
        headers=host_headers,
    )
    assert story_progression.status_code == 200
    rows = story_progression.json()
    row = next(item for item in rows if item["user_id"] == player_auth["user"]["id"])
    assert row["xp_total"] == 1050


def test_progression_award_requires_story_owner_and_participant(client):
    host_auth = _register(client, "progress-owner@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    outsider_auth = _register(client, "progress-outsider@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_auth['access_token']}"}
    target_auth = _register(client, "progress-target@example.com")

    story = _create_story(client, host_headers, "Owner Story")
    bundle = _create_and_start_session(client, host_headers, story["id"])

    not_joined_award = client.post(
        "/api/v1/progression/award",
        json={
            "story_id": story["id"],
            "user_id": target_auth["user"]["id"],
            "xp_delta": 100,
        },
        headers=host_headers,
    )
    assert not_joined_award.status_code == 404

    target_headers = {"Authorization": f"Bearer {target_auth['access_token']}"}
    join_resp = client.post(
        "/api/v1/sessions/join",
        json={
            "join_token": bundle["started"]["join_token"],
            "device_fingerprint": "progress-target-device",
        },
        headers=target_headers,
    )
    assert join_resp.status_code == 200

    outsider_award = client.post(
        "/api/v1/progression/award",
        json={
            "story_id": story["id"],
            "user_id": target_auth["user"]["id"],
            "xp_delta": 100,
        },
        headers=outsider_headers,
    )
    assert outsider_award.status_code == 404
