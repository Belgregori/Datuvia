import uuid

from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_register_and_login():
    email = f"auth-{uuid.uuid4().hex[:8]}@example.com"
    password = "testpass123"

    with _client() as client:
        created = client.post("/api/auth/register", json={"email": email, "password": password})
        assert created.status_code == 201
        assert created.json()["email"] == email

        duplicate = client.post("/api/auth/register", json={"email": email, "password": password})
        assert duplicate.status_code == 409

        weak = client.post(
            "/api/auth/register",
            json={"email": f"weak-{uuid.uuid4().hex[:8]}@example.com", "password": "corta"},
        )
        assert weak.status_code == 400

        logged = client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
        )
        assert logged.status_code == 200
        assert logged.json()["access_token"]
        assert logged.json()["token_type"] == "bearer"

        rejected = client.post(
            "/api/auth/login",
            data={"username": email, "password": "incorrecta"},
        )
        assert rejected.status_code == 401
