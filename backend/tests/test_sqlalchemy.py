import os

import pytest
from sqlalchemy import URL, create_engine, text


def test_sqlalchemy_select_one(monkeypatch):
    test_database = os.getenv("TEST_PGDATABASE")
    if not test_database:
        pytest.skip("Set TEST_PGDATABASE to a dedicated test database")
    if test_database == os.getenv("PGDATABASE", "postgres"):
        pytest.fail("TEST_PGDATABASE must differ from the development database")

    test_url = URL.create(
        "postgresql+psycopg",
        username=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        host=os.getenv("PGHOST", "127.0.0.1"),
        port=int(os.getenv("PGPORT", "5432")),
        database=test_database,
    )
    test_engine = create_engine(test_url)
    try:
        with test_engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            value = "a'; DROP TABLE should_not_exist; --"
            assert connection.execute(text("SELECT :value"), {"value": value}).scalar_one() == value
    finally:
        test_engine.dispose()
