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
        json={"title": title, "description": "Story for memory tests"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _embedding(index: int, size: int = 1536) -> list[float]:
    values = [0.0] * size
    values[index] = 1.0
    return values


def test_memory_chunk_create_and_search(client):
    host_auth = _register(client, "memory-host@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Memory Story")

    first_chunk = client.post(
        "/api/v1/memory/chunks",
        json={
            "story_id": story["id"],
            "memory_type": "quest",
            "content": "The ritual requires three moonstones.",
            "embedding": _embedding(0),
            "metadata_json": {"source": "gm-note"},
        },
        headers=host_headers,
    )
    assert first_chunk.status_code == 201

    second_chunk = client.post(
        "/api/v1/memory/chunks",
        json={
            "story_id": story["id"],
            "memory_type": "npc",
            "content": "Captain Ilyra distrusts the council.",
            "embedding": _embedding(1),
            "metadata_json": {"source": "timeline"},
        },
        headers=host_headers,
    )
    assert second_chunk.status_code == 201

    search = client.post(
        "/api/v1/memory/search",
        json={
            "story_id": story["id"],
            "query_embedding": _embedding(0),
            "limit": 2,
        },
        headers=host_headers,
    )
    assert search.status_code == 200
    results = search.json()
    assert len(results) == 2
    assert results[0]["chunk"]["memory_type"] == "quest"
    assert results[0]["chunk"]["content"] == "The ritual requires three moonstones."
    assert results[0]["similarity"] >= results[1]["similarity"]


def test_memory_chunk_requires_story_owner(client):
    host_auth = _register(client, "memory-owner@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    outsider_auth = _register(client, "memory-outsider@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_auth['access_token']}"}
    story = _create_story(client, host_headers, "Owner Memory Story")

    create_forbidden = client.post(
        "/api/v1/memory/chunks",
        json={
            "story_id": story["id"],
            "memory_type": "fact",
            "content": "Hidden fact",
            "embedding": _embedding(0),
        },
        headers=outsider_headers,
    )
    assert create_forbidden.status_code == 404

    search_forbidden = client.post(
        "/api/v1/memory/search",
        json={
            "story_id": story["id"],
            "query_embedding": _embedding(0),
            "limit": 5,
        },
        headers=outsider_headers,
    )
    assert search_forbidden.status_code == 404


def test_memory_embedding_dimension_validation(client):
    host_auth = _register(client, "memory-dimension@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Dimension Story")

    invalid_create = client.post(
        "/api/v1/memory/chunks",
        json={
            "story_id": story["id"],
            "memory_type": "fact",
            "content": "Short vector",
            "embedding": [0.1, 0.2, 0.3],
        },
        headers=host_headers,
    )
    assert invalid_create.status_code == 422

    invalid_search = client.post(
        "/api/v1/memory/search",
        json={
            "story_id": story["id"],
            "query_embedding": [0.9, 0.1],
            "limit": 3,
        },
        headers=host_headers,
    )
    assert invalid_search.status_code == 422
