import os

from fastapi.testclient import TestClient

from app.main import app


def test_frontend_origin_can_read_health():
    origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    with TestClient(app) as client:
        response = client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_other_origin_has_no_cors_permission():
    with TestClient(app) as client:
        response = client.get("/health", headers={"Origin": "https://untrusted.example"})

    assert "access-control-allow-origin" not in response.headers
