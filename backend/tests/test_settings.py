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
    assert current["tts_provider"] == "codex"
    assert current["tts_model"] is None
    assert current["tts_voice"] == "alloy"
    assert current["language"] == "en"
    assert current["voice_mode"] == "webrtc_with_fallback"

    update_response = client.put(
        "/api/v1/settings/me",
        headers=headers,
        json={
            "llm_provider": "ollama",
            "llm_model": "llama3.2:3b",
            "tts_provider": "claude",
            "tts_model": "claude-tts-compatible",
            "tts_voice": "shimmer",
            "language": "fr",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["llm_provider"] == "ollama"
    assert updated["llm_model"] == "llama3.2:3b"
    assert updated["tts_provider"] == "claude"
    assert updated["tts_model"] == "claude-tts-compatible"
    assert updated["tts_voice"] == "shimmer"
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


def test_settings_update_rejects_invalid_tts_voice(client):
    auth = _register(client, "settings-invalid-voice@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    response = client.put(
        "/api/v1/settings/me",
        headers=headers,
        json={"tts_provider": "codex", "tts_voice": "bad voice!"},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"]["message"] == "Invalid TTS settings"
    assert payload["detail"]["issues"]


def test_tts_provider_catalog_endpoint(client):
    auth = _register(client, "settings-tts-catalog@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    client.app.state.settings.tts_codex_api_key = "test-key"
    response = client.get("/api/v1/settings/tts/providers", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["providers"]) == 3
    providers = {item["provider"]: item for item in payload["providers"]}
    assert providers["codex"]["configured"] is True
    assert providers["codex"]["default_model"] == client.app.state.settings.tts_codex_model
    assert providers["ollama"]["configured"] is True


def test_tts_profile_validation_endpoint(client):
    auth = _register(client, "settings-tts-validate@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    response = client.post(
        "/api/v1/settings/tts/validate",
        headers=headers,
        json={"provider": "codex", "model": "bad model!", "voice": "alloy"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert any("Model must use letters" in issue for issue in payload["issues"])


def test_tts_health_endpoint_ollama_success(client, monkeypatch):
    auth = _register(client, "settings-tts-health-ollama@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    monkeypatch.setattr(
        settings_endpoint,
        "_probe_ollama_models",
        lambda base_url, timeout_seconds=2: (True, ["llama3.2:3b", "mistral:7b"]),
    )
    response = client.post(
        "/api/v1/settings/tts/health",
        headers=headers,
        json={"provider": "ollama", "model": "llama3.2:3b", "voice": "alloy"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["healthy"] is True
    assert payload["configured"] is True
    assert payload["reachable"] is True
    assert payload["model_available"] is True


def test_tts_health_endpoint_codex_requires_configuration(client):
    auth = _register(client, "settings-tts-health-codex@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    response = client.post(
        "/api/v1/settings/tts/health",
        headers=headers,
        json={"provider": "codex", "model": "gpt-4o-mini-tts", "voice": "alloy"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["healthy"] is False
    assert payload["configured"] is False
    assert any("not configured" in issue for issue in payload["issues"])
