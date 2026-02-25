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
        json={"title": title, "description": "Story for character tests"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_and_start_session(client, host_headers: dict[str, str], story_id: str) -> dict:
    create_response = client.post(
        "/api/v1/sessions",
        json={"story_id": story_id, "max_players": 4},
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
    return start_response.json()


def test_host_can_create_character_and_player_can_read_only(client):
    host_auth = _register(client, "character-host@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Character Story")
    started = _create_and_start_session(client, host_headers, story["id"])

    player_auth = _register(client, "character-player@example.com")
    player_headers = {"Authorization": f"Bearer {player_auth['access_token']}"}
    join_response = client.post(
        "/api/v1/sessions/join",
        json={
            "join_token": started["join_token"],
            "device_fingerprint": "character-player-device",
        },
        headers=player_headers,
    )
    assert join_response.status_code == 200

    create_response = client.post(
        "/api/v1/characters",
        json={
            "story_id": story["id"],
            "name": "Ari Silverleaf",
            "race": "Elf",
            "character_class": "Wizard",
            "background": "Sage",
            "max_hp": 8,
            "armor_class": 12,
            "creation_mode": "auto",
        },
        headers=host_headers,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["creation_mode"] == "auto"
    assert created["abilities"]["strength"] == 15

    list_response = client.get(
        f"/api/v1/characters?story_id={story['id']}",
        headers=player_headers,
    )
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "Ari Silverleaf"

    player_create_response = client.post(
        "/api/v1/characters",
        json={
            "story_id": story["id"],
            "name": "Nera Dawnstep",
            "race": "Human",
            "character_class": "Cleric",
            "background": "Acolyte",
            "max_hp": 9,
            "creation_mode": "auto",
        },
        headers=player_headers,
    )
    assert player_create_response.status_code == 403
    assert player_create_response.json()["detail"] == "Host access required"


def test_dice_creation_requires_roll_assignment_match(client):
    auth = _register(client, "character-dice@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    story = _create_story(client, headers, "Dice Story")

    valid_response = client.post(
        "/api/v1/characters",
        json={
            "story_id": story["id"],
            "name": "Brom Ironforge",
            "race": "Dwarf",
            "character_class": "Fighter",
            "background": "Soldier",
            "max_hp": 12,
            "creation_mode": "player_dice",
            "ability_rolls": [15, 14, 13, 12, 10, 8],
            "abilities": {
                "strength": 15,
                "dexterity": 12,
                "constitution": 14,
                "intelligence": 8,
                "wisdom": 10,
                "charisma": 13,
            },
        },
        headers=headers,
    )
    assert valid_response.status_code == 201
    assert valid_response.json()["creation_rolls"] == [15, 14, 13, 12, 10, 8]

    invalid_response = client.post(
        "/api/v1/characters",
        json={
            "story_id": story["id"],
            "name": "Invalid Build",
            "race": "Human",
            "character_class": "Rogue",
            "background": "Criminal",
            "max_hp": 10,
            "creation_mode": "player_dice",
            "ability_rolls": [15, 14, 13, 12, 10, 8],
            "abilities": {
                "strength": 16,
                "dexterity": 12,
                "constitution": 14,
                "intelligence": 8,
                "wisdom": 10,
                "charisma": 13,
            },
        },
        headers=headers,
    )
    assert invalid_response.status_code == 422


def test_save_restore_preserves_characters(client):
    auth = _register(client, "character-save@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    story = _create_story(client, headers, "Save Character Story")

    create_response = client.post(
        "/api/v1/characters",
        json={
            "story_id": story["id"],
            "name": "Lyra Moonfall",
            "race": "Half-Elf",
            "character_class": "Bard",
            "background": "Noble",
            "max_hp": 9,
            "creation_mode": "auto",
        },
        headers=headers,
    )
    assert create_response.status_code == 201

    save_response = client.post(
        "/api/v1/saves",
        json={"story_id": story["id"], "label": "Character Snapshot"},
        headers=headers,
    )
    assert save_response.status_code == 201
    save = save_response.json()

    detail_response = client.get(f"/api/v1/saves/{save['id']}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["snapshot_json"]["characters"]) == 1
    assert detail["snapshot_json"]["characters"][0]["name"] == "Lyra Moonfall"

    restore_response = client.post(
        f"/api/v1/saves/{save['id']}/restore",
        json={"title": "Restored Character Story"},
        headers=headers,
    )
    assert restore_response.status_code == 200
    restored_story_id = restore_response.json()["story"]["id"]

    restored_characters_response = client.get(
        f"/api/v1/characters?story_id={restored_story_id}",
        headers=headers,
    )
    assert restored_characters_response.status_code == 200
    restored_characters = restored_characters_response.json()
    assert len(restored_characters) == 1
    assert restored_characters[0]["name"] == "Lyra Moonfall"


def test_character_srd_options_endpoint(client):
    auth = _register(client, "character-options@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    response = client.get("/api/v1/characters/srd-options", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert "Wizard" in payload["classes"]
    assert payload["ability_keys"] == [
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
    ]
