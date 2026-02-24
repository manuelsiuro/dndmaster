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
        json={"title": title, "description": "Story for save tests"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_timeline_event(client, headers: dict[str, str], story_id: str, text: str) -> None:
    response = client.post(
        "/api/v1/timeline/events",
        json={
            "story_id": story_id,
            "event_type": "player_action",
            "text_content": text,
            "language": "en",
        },
        headers=headers,
    )
    assert response.status_code == 201


def test_story_save_create_list_detail_restore_flow(client):
    host_auth = _register(client, "save-host@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Echoes of the Vault")

    _create_timeline_event(client, host_headers, story["id"], "I inspect the runes.")
    _create_timeline_event(client, host_headers, story["id"], "I pull the hidden lever.")

    session_resp = client.post(
        "/api/v1/sessions",
        json={"story_id": story["id"], "max_players": 4},
        headers=host_headers,
    )
    assert session_resp.status_code == 201

    create_save_resp = client.post(
        "/api/v1/saves",
        json={"story_id": story["id"], "label": "Before Vault Door"},
        headers=host_headers,
    )
    assert create_save_resp.status_code == 201
    save = create_save_resp.json()
    assert save["timeline_event_count"] == 2
    assert save["session_count"] == 1
    assert save["label"] == "Before Vault Door"

    list_resp = client.get(f"/api/v1/saves?story_id={story['id']}", headers=host_headers)
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert len(listed) == 1
    assert listed[0]["id"] == save["id"]

    detail_resp = client.get(f"/api/v1/saves/{save['id']}", headers=host_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["snapshot_json"]["story"]["title"] == "Echoes of the Vault"
    assert len(detail["snapshot_json"]["timeline_events"]) == 2

    restore_resp = client.post(
        f"/api/v1/saves/{save['id']}/restore",
        json={"title": "Echoes of the Vault (Restore A)"},
        headers=host_headers,
    )
    assert restore_resp.status_code == 200
    restored = restore_resp.json()
    assert restored["story"]["title"] == "Echoes of the Vault (Restore A)"
    assert restored["timeline_events_restored"] == 2

    restored_story_id = restored["story"]["id"]
    restored_events_resp = client.get(
        f"/api/v1/timeline/events?story_id={restored_story_id}&limit=10&offset=0",
        headers=host_headers,
    )
    assert restored_events_resp.status_code == 200
    restored_events = restored_events_resp.json()
    assert len(restored_events) == 2


def test_story_save_access_is_owner_only(client):
    host_auth = _register(client, "save-owner@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Owner Story")

    save_resp = client.post(
        "/api/v1/saves",
        json={"story_id": story["id"], "label": "Owner Save"},
        headers=host_headers,
    )
    assert save_resp.status_code == 201
    save_id = save_resp.json()["id"]

    outsider_auth = _register(client, "save-outsider@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_auth['access_token']}"}

    list_resp = client.get(f"/api/v1/saves?story_id={story['id']}", headers=outsider_headers)
    assert list_resp.status_code == 404

    detail_resp = client.get(f"/api/v1/saves/{save_id}", headers=outsider_headers)
    assert detail_resp.status_code == 404

    restore_resp = client.post(
        f"/api/v1/saves/{save_id}/restore",
        json={"title": "Illegal Restore"},
        headers=outsider_headers,
    )
    assert restore_resp.status_code == 404
