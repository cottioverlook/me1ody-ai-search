import uuid

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.utils.user_context import AnonymousSessionMiddleware, create_session_token, get_user_id, verify_session_token


def test_signed_session_round_trip():
    secret = b"test-session-secret-that-is-at-least-32-bytes"
    user_id = str(uuid.uuid4())
    token = create_session_token(user_id, secret, now=1_000)

    assert verify_session_token(token, secret, now=1_001) == user_id


def test_signed_session_rejects_tampering_and_expiry():
    secret = b"test-session-secret-that-is-at-least-32-bytes"
    user_id = str(uuid.uuid4())
    token = create_session_token(user_id, secret, now=1_000)

    assert verify_session_token(token + "tampered", secret, now=1_001) is None
    assert verify_session_token(token, b"another-test-secret-that-is-at-least-32-bytes", now=1_001) is None
    assert verify_session_token(token, secret, now=1_000 + 31 * 24 * 60 * 60) is None


def test_signed_session_rejects_non_uuid_identity():
    secret = b"test-session-secret-that-is-at-least-32-bytes"
    token = create_session_token("attacker-controlled-id", secret, now=1_000)

    assert verify_session_token(token, secret, now=1_001) is None


def test_middleware_ignores_client_supplied_user_id_and_keeps_cookie_identity(monkeypatch):
    monkeypatch.setattr("app.config.settings.app_env", "test")
    monkeypatch.setattr("app.config.settings.session_secret", "test-session-secret-that-is-at-least-32-bytes")
    app = FastAPI()
    app.add_middleware(AnonymousSessionMiddleware)

    @app.get("/whoami")
    async def whoami(request: Request):
        return {"user_id": get_user_id(request)}

    client = TestClient(app)
    first = client.get("/whoami", headers={"x-user-id": "attacker-controlled-id"})
    second = client.get("/whoami", headers={"x-user-id": "different-attacker-id"})

    assert first.status_code == 200
    assert first.json()["user_id"] != "attacker-controlled-id"
    assert second.json()["user_id"] == first.json()["user_id"]
    assert "HttpOnly" in first.headers["set-cookie"]
