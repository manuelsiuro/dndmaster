def test_register_login_me_flow(client):
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "player1@example.com", "password": "SuperSecret123"},
    )
    assert register_resp.status_code == 201
    register_data = register_resp.json()

    token = register_data["access_token"]
    assert token
    assert register_data["user"]["email"] == "player1@example.com"

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "player1@example.com", "password": "SuperSecret123"},
    )
    assert login_resp.status_code == 200

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "player1@example.com"


def test_register_duplicate_email_returns_conflict(client):
    payload = {"email": "dup@example.com", "password": "SuperSecret123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    duplicate_resp = client.post("/api/v1/auth/register", json=payload)
    assert duplicate_resp.status_code == 409
