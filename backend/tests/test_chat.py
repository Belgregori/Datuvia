import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class _FakeStream:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        return None

    def iter_lines(self):
        yield 'data: {"choices":[{"delta":{"content":"respuesta simulada"}}]}'
        yield "data: [DONE]"


class _FakeClient:
    def __init__(self, *_args, **_kwargs):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def stream(self, *_args, **_kwargs):
        return _FakeStream()


def test_chat_uses_mocked_llm_without_network():
    email = f"chat-{uuid.uuid4().hex[:8]}@example.com"
    password = "testpass123"

    with TestClient(app) as client:
        assert client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
        ).status_code == 201
        token = client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        workspace = client.post(
            "/api/workspaces",
            headers=headers,
            json={"name": "Test chat"},
        )
        assert workspace.status_code == 201
        workspace_id = workspace.json()["id"]

        uploaded = client.post(
            "/api/docs",
            headers=headers,
            data={"workspace_id": workspace_id, "title": "Nota"},
            files={"file": ("nota.txt", b"El vector es una magnitud con direccion.", "text/plain")},
        )
        assert uploaded.status_code == 201

        listed = client.get(f"/api/docs?workspace_id={workspace_id}", headers=headers)
        assert listed.status_code == 200
        assert listed.json()[0]["status"] == "listo"

        with (
            patch(
                "app.services.rag_service._chat_provider",
                return_value=("https://example.test/v1/chat/completions", "test-key", "test-model"),
            ),
            patch("app.services.rag_service.httpx.Client", _FakeClient),
        ):
            response = client.post(
                "/api/chat",
                headers=headers,
                json={"workspace_id": workspace_id, "question": "que es un vector?"},
            )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "respuesta simulada" in response.text
        assert '"type": "sources"' in response.text
        assert '"type": "done"' in response.text
