import os

import pytest
from sqlalchemy import text


def test_sqlalchemy_select_one(monkeypatch):
    test_database = os.getenv("TEST_PGDATABASE")
    if not test_database:
        pytest.skip("Set TEST_PGDATABASE to a dedicated test database")
    if test_database == os.getenv("PGDATABASE", "postgres"):
        pytest.fail("TEST_PGDATABASE must differ from the development database")

    monkeypatch.setenv("PGDATABASE", test_database)
    from app.database import SessionLocal

    with SessionLocal() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1
