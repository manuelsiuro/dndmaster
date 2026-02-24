from app.api.v1.endpoints import settings as settings_endpoint


def _register(client, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SuperSecret123"},
    )
    assert response.status_code == 201
    return response.json()


def test_user_settings_defaults_and_update(client):
    auth = _register(client, "settings-user@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    get_response = client.get("/api/v1/settings/me", headers=headers)
    assert get_response.status_code == 200
    current = get_response.json()
    assert current["llm_provider"] == "codex"
    assert current["language"] == "en"
    assert current["voice_mode"] == "webrtc_with_fallback"

    update_response = client.put(
        "/api/v1/settings/me",
        headers=headers,
        json={
            "llm_provider": "ollama",
            "llm_model": "llama3.2:3b",
            "language": "fr",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["llm_provider"] == "ollama"
    assert updated["llm_model"] == "llama3.2:3b"
    assert updated["language"] == "fr"


def test_ollama_model_list_endpoint(client, monkeypatch):
    auth = _register(client, "settings-models@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    monkeypatch.setattr(
        settings_endpoint,
        "_fetch_ollama_models",
        lambda _base_url: ["llama3.2:3b", "mistral:7b"],
    )

    response = client.get("/api/v1/settings/ollama/models", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["models"] == ["llama3.2:3b", "mistral:7b"]
