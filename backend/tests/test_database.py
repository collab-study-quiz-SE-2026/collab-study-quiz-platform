import os

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_database_health(monkeypatch):
    test_database = os.getenv("TEST_PGDATABASE")
    if not test_database:
        pytest.skip("Set TEST_PGDATABASE to a dedicated test database")
    if test_database == os.getenv("PGDATABASE", "postgres"):
        pytest.fail("TEST_PGDATABASE must differ from the development database")

    monkeypatch.setenv("PGDATABASE", test_database)
    with TestClient(app) as client:
        response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_database_unavailable(monkeypatch):
    def unavailable(**kwargs):
        raise psycopg.OperationalError("Simulated private connection details")

    monkeypatch.setattr(psycopg, "connect", unavailable)
    with TestClient(app) as client:
        response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
