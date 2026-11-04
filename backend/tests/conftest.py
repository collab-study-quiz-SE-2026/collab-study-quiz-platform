from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole


@pytest.fixture
def test_setup(monkeypatch) -> Generator[tuple, None, None]:
    monkeypatch.setenv("JWT_SECRET_KEY", "testing-jwt-secret-key-for-test-suite-12345")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with testing_session() as session:
        student1 = User(
            email="author@example.com",
            password_hash=hash_password("authorpass"),
            role=UserRole.STUDENT,
        )
        student2 = User(
            email="otherstudent@example.com",
            password_hash=hash_password("otherpass"),
            role=UserRole.STUDENT,
        )
        moderator = User(
            email="moderator@example.com",
            password_hash=hash_password("modpass"),
            role=UserRole.MODERATOR,
        )
        session.add_all([student1, student2, moderator])
        session.commit()
        session.refresh(student1)
        session.refresh(student2)
        session.refresh(moderator)
        tokens = (
            create_access_token(student1),
            create_access_token(student2),
            create_access_token(moderator),
        )

    with TestClient(app) as client:
        yield client, testing_session, student1, tokens[0], student2, tokens[1], moderator, tokens[2]

    app.dependency_overrides.clear()
