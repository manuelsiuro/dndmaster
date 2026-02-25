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
        json={"title": title, "description": "Story for orchestration tests"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_orchestration_context_assembles_memory_summary_timeline(client):
    host_auth = _register(client, "orchestration-host@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    story = _create_story(client, host_headers, "Orchestration Story")

    seed_text = "The hidden vault is beneath the bell tower."
    chunk_resp = client.post(
        "/api/v1/memory/chunks",
        json={
            "story_id": story["id"],
            "memory_type": "location",
            "content": seed_text,
            "embedding": hash_text_embedding(seed_text, 1536),
            "metadata_json": {"source": "orchestration-test"},
        },
        headers=host_headers,
    )
    assert chunk_resp.status_code == 201
    chunk = chunk_resp.json()

    timeline_resp = client.post(
        "/api/v1/timeline/events",
        json={
            "story_id": story["id"],
            "event_type": "gm_prompt",
            "text_content": "Thunder rolls over the tower and the town square clears.",
            "language": "en",
        },
        headers=host_headers,
    )
    assert timeline_resp.status_code == 201

    summary_resp = client.post(
        "/api/v1/memory/summaries/generate",
        json={
            "story_id": story["id"],
            "summary_window": "latest",
            "max_events": 20,
        },
        headers=host_headers,
    )
    assert summary_resp.status_code == 201

    context_resp = client.post(
        "/api/v1/orchestration/context",
        json={
            "story_id": story["id"],
            "query_text": "Where is the hidden vault?",
            "language": "en",
            "memory_limit": 3,
            "summary_limit": 1,
            "timeline_limit": 1,
        },
        headers=host_headers,
    )
    assert context_resp.status_code == 200
    payload = context_resp.json()

    assert payload["story_id"] == story["id"]
    assert payload["query_text"] == "Where is the hidden vault?"
    assert payload["retrieval_audit_id"]
    assert len(payload["retrieved_memory"]) >= 1
    assert payload["retrieved_memory"][0]["id"] == chunk["id"]
    assert len(payload["summaries"]) == 1
    assert len(payload["recent_events"]) == 1
    assert "Retrieved memory:" in payload["prompt_context"]
    assert "Recent summaries:" in payload["prompt_context"]
    assert "Recent timeline events:" in payload["prompt_context"]

    audit_resp = client.get(
        f"/api/v1/memory/audit?story_id={story['id']}",
        headers=host_headers,
    )
    assert audit_resp.status_code == 200
    audits = audit_resp.json()
    assert len(audits) == 1
    assert audits[0]["id"] == payload["retrieval_audit_id"]
    assert audits[0]["query_text"] == "Where is the hidden vault?"
    assert audits[0]["retrieved_memory_ids"][0] == chunk["id"]
    assert audits[0]["applied_memory_ids"][0] == chunk["id"]


def test_orchestration_context_requires_story_owner(client):
    host_auth = _register(client, "orchestration-owner@example.com")
    host_headers = {"Authorization": f"Bearer {host_auth['access_token']}"}
    outsider_auth = _register(client, "orchestration-outsider@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_auth['access_token']}"}
    story = _create_story(client, host_headers, "Protected Orchestration Story")

    response = client.post(
        "/api/v1/orchestration/context",
        json={
            "story_id": story["id"],
            "query_text": "What happened in this story?",
        },
        headers=outsider_headers,
    )
    assert response.status_code == 404
