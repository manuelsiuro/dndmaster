from app.services.embedding import hash_text_embedding


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


def test_memory_search_supports_text_query_without_embedding(client):
    host_auth = _register(client, "memory-text-search@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Memory Text Search Story")

    seed_text = "The obsidian vault is hidden beneath the bell tower."
    created = client.post(
        "/api/v1/memory/chunks",
        json={
            "story_id": story["id"],
            "memory_type": "location",
            "content": seed_text,
            "embedding": hash_text_embedding(seed_text, 1536),
            "metadata_json": {"source": "manual"},
        },
        headers=host_headers,
    )
    assert created.status_code == 201
    created_chunk = created.json()

    search = client.post(
        "/api/v1/memory/search",
        json={
            "story_id": story["id"],
            "query_text": "Where is the obsidian vault hidden?",
            "limit": 3,
        },
        headers=host_headers,
    )
    assert search.status_code == 200
    results = search.json()
    assert len(results) == 1
    assert results[0]["chunk"]["id"] == created_chunk["id"]


def test_memory_search_requires_query_embedding_or_text(client):
    host_auth = _register(client, "memory-empty-query@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Memory Query Validation Story")

    invalid_search = client.post(
        "/api/v1/memory/search",
        json={
            "story_id": story["id"],
            "limit": 2,
        },
        headers=host_headers,
    )
    assert invalid_search.status_code == 422


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


def test_timeline_event_auto_ingests_memory_chunk(client):
    host_auth = _register(client, "memory-timeline@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Timeline Memory Story")

    event_resp = client.post(
        "/api/v1/timeline/events",
        json={
            "story_id": story["id"],
            "event_type": "choice_prompt",
            "text_content": "Choose the hidden tunnel or the collapsed hall.",
            "language": "en",
            "transcript_segments": [
                {
                    "content": "Choose the hidden tunnel or the collapsed hall.",
                    "language": "en",
                    "confidence": 0.97,
                }
            ],
        },
        headers=host_headers,
    )
    assert event_resp.status_code == 201
    event = event_resp.json()

    chunks_resp = client.get(
        f"/api/v1/memory/chunks?story_id={story['id']}",
        headers=host_headers,
    )
    assert chunks_resp.status_code == 200
    chunks = chunks_resp.json()
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["source_event_id"] == event["id"]
    assert chunk["memory_type"] == "quest"
    assert "hidden tunnel" in chunk["content"]


def test_memory_summary_generation_and_listing(client):
    host_auth = _register(client, "memory-summary@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Summary Story")

    timeline_resp = client.post(
        "/api/v1/timeline/events",
        json={
            "story_id": story["id"],
            "event_type": "outcome",
            "text_content": "The party negotiates safe passage with the marsh druids.",
            "language": "en",
        },
        headers=host_headers,
    )
    assert timeline_resp.status_code == 201

    generate_resp = client.post(
        "/api/v1/memory/summaries/generate",
        json={
            "story_id": story["id"],
            "summary_window": "latest",
            "max_events": 20,
        },
        headers=host_headers,
    )
    assert generate_resp.status_code == 201
    summary = generate_resp.json()
    assert summary["story_id"] == story["id"]
    assert summary["summary_window"] == "latest"
    assert "Window events:" in summary["summary_text"]

    summaries_resp = client.get(
        f"/api/v1/memory/summaries?story_id={story['id']}",
        headers=host_headers,
    )
    assert summaries_resp.status_code == 200
    summaries = summaries_resp.json()
    assert len(summaries) == 1
    assert summaries[0]["id"] == summary["id"]

    chunks_resp = client.get(
        f"/api/v1/memory/chunks?story_id={story['id']}",
        headers=host_headers,
    )
    assert chunks_resp.status_code == 200
    chunks = chunks_resp.json()
    summary_chunks = [item for item in chunks if item["memory_type"] == "summary"]
    assert len(summary_chunks) >= 1
    generated = [item for item in summary_chunks if item["metadata_json"].get("summary_window")]
    assert len(generated) == 1
    assert generated[0]["metadata_json"]["summary_window"] == "latest"


def test_memory_search_records_retrieval_audit_event(client):
    host_auth = _register(client, "memory-audit@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Audit Story")

    created_resp = client.post(
        "/api/v1/memory/chunks",
        json={
            "story_id": story["id"],
            "memory_type": "npc",
            "content": "Aria the cartographer guards the flood maps.",
            "embedding": _embedding(4),
            "metadata_json": {"source": "test"},
        },
        headers=host_headers,
    )
    assert created_resp.status_code == 201
    created_chunk = created_resp.json()

    search_resp = client.post(
        "/api/v1/memory/search",
        json={
            "story_id": story["id"],
            "query_embedding": _embedding(4),
            "query_text": "Who guards the flood maps?",
            "applied_memory_ids": [created_chunk["id"]],
            "limit": 3,
        },
        headers=host_headers,
    )
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) == 1

    audit_resp = client.get(
        f"/api/v1/memory/audit?story_id={story['id']}",
        headers=host_headers,
    )
    assert audit_resp.status_code == 200
    audits = audit_resp.json()
    assert len(audits) == 1
    assert audits[0]["query_text"] == "Who guards the flood maps?"
    assert audits[0]["retrieved_memory_ids"] == [created_chunk["id"]]
    assert audits[0]["applied_memory_ids"] == [created_chunk["id"]]
