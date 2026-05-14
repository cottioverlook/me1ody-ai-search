import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.utils.logging import RequestLoggingMiddleware, configure_logging
from app.utils.security import PublicAccessMiddleware


def test_configure_logging_accepts_invalid_level():
    configure_logging("NOT_A_LEVEL")

    assert logging.getLogger().level in {logging.INFO, logging.WARNING}


def test_request_logging_middleware_adds_request_id_header():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/ping", headers={"x-request-id": "test-request"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request"


def test_request_logging_middleware_logs_structured_record(caplog):
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    client = TestClient(app)
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/ping")

    assert response.status_code == 200
    records = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "app.request"
    ]
    assert records[-1]["event"] == "request"
    assert records[-1]["path"] == "/ping"
    assert records[-1]["status_code"] == 200


def test_public_access_middleware_requires_test_token(monkeypatch):
    monkeypatch.setattr("app.config.settings.app_env", "local")
    monkeypatch.setattr("app.config.settings.public_test_token", "secret")
    monkeypatch.setattr("app.config.settings.rate_limit_per_minute", 0)
    monkeypatch.setattr("app.config.settings.rate_limit_per_day", 0)

    app = FastAPI()
    app.add_middleware(PublicAccessMiddleware)

    @app.get("/api/private")
    async def private():
        return {"ok": True}

    client = TestClient(app)

    assert client.get("/api/private").status_code == 401
    assert client.get("/api/private", headers={"x-test-token": "secret"}).status_code == 200


def test_public_access_middleware_rate_limits_by_ip(monkeypatch):
    monkeypatch.setattr("app.config.settings.app_env", "render")
    monkeypatch.setattr("app.config.settings.public_test_token", "")
    monkeypatch.setattr("app.config.settings.rate_limit_per_minute", 1)
    monkeypatch.setattr("app.config.settings.rate_limit_per_day", 0)

    app = FastAPI()
    app.add_middleware(PublicAccessMiddleware)

    @app.get("/api/private")
    async def private():
        return {"ok": True}

    client = TestClient(app)

    assert client.get("/api/private", headers={"x-forwarded-for": "203.0.113.1"}).status_code == 200
    assert client.get("/api/private", headers={"x-forwarded-for": "203.0.113.1"}).status_code == 429
    assert client.get("/api/private", headers={"x-forwarded-for": "203.0.113.2"}).status_code == 200
