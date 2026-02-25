import uuid


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
        json={"title": title, "description": "Story for postgres memory tests"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _embedding(index: int, size: int = 1536) -> list[float]:
    values = [0.0] * size
    values[index] = 1.0
    return values


def test_postgres_memory_search_and_orchestration_context(postgres_client):
    suffix = uuid.uuid4().hex[:8]
    host_auth = _register(postgres_client, f"pg-memory-host-{suffix}@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(postgres_client, host_headers, f"PG Memory Story {suffix}")

    quest_chunk = postgres_client.post(
        "/api/v1/memory/chunks",
        json={
            "story_id": story["id"],
            "memory_type": "quest",
            "content": "Recover the ember crown from the basalt crypt.",
            "embedding": _embedding(0),
            "metadata_json": {"source": "pgvector-test"},
        },
        headers=host_headers,
    )
    assert quest_chunk.status_code == 201
    quest_chunk_id = quest_chunk.json()["id"]

    npc_chunk = postgres_client.post(
        "/api/v1/memory/chunks",
        json={
            "story_id": story["id"],
            "memory_type": "npc",
            "content": "Warden Telra guards the crypt gate.",
            "embedding": _embedding(1),
            "metadata_json": {"source": "pgvector-test"},
        },
        headers=host_headers,
    )
    assert npc_chunk.status_code == 201

    summary_resp = postgres_client.post(
        "/api/v1/memory/summaries/generate",
        json={
            "story_id": story["id"],
            "summary_window": "latest",
            "max_events": 10,
        },
        headers=host_headers,
    )
    assert summary_resp.status_code == 201

    search_resp = postgres_client.post(
        "/api/v1/memory/search",
        json={
            "story_id": story["id"],
            "query_embedding": _embedding(0),
            "query_text": "Where is the ember crown quest?",
            "limit": 2,
        },
        headers=host_headers,
    )
    assert search_resp.status_code == 200
    search_results = search_resp.json()
    assert len(search_results) == 2
    assert search_results[0]["chunk"]["id"] == quest_chunk_id

    context_resp = postgres_client.post(
        "/api/v1/orchestration/context",
        json={
            "story_id": story["id"],
            "query_text": "Summarize current quest priorities.",
            "language": "en",
            "memory_limit": 2,
            "summary_limit": 1,
            "timeline_limit": 0,
        },
        headers=host_headers,
    )
    assert context_resp.status_code == 200
    context_payload = context_resp.json()
    assert context_payload["retrieval_audit_id"]
    assert len(context_payload["retrieved_memory"]) == 2
    assert len(context_payload["summaries"]) == 1
    assert context_payload["recent_events"] == []
    assert "Retrieved memory:" in context_payload["prompt_context"]

    audit_resp = postgres_client.get(
        f"/api/v1/memory/audit?story_id={story['id']}",
        headers=host_headers,
    )
    assert audit_resp.status_code == 200
    audits = audit_resp.json()
    assert len(audits) >= 2
