import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_app_has_health_route():
    routes = {route.path for route in app.routes}
    assert "/health" in routes


def test_health_degraded_redis(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["api"] is True
    assert body["database"] is True
    assert body["redis"] is False
    assert body["status"] == "degraded"


def test_health_all_ok(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class StubRedis:
        def ping(self) -> bool:
            return True

    monkeypatch.setattr("app.main.redis.Redis.from_url", lambda *args, **kwargs: StubRedis())

    response = client.get("/health")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["api"] is True
    assert body["database"] is True
    assert body["redis"] is True
    assert body["status"] == "ok"


def test_health_degraded_database(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_connect(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("app.main.engine.connect", raise_connect)

    response = client.get("/health")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["api"] is True
    assert body["database"] is False
    assert body["status"] == "degraded"
