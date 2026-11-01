import os
from collections.abc import Generator
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole


@pytest.fixture
def auth_client(monkeypatch) -> Generator[TestClient, None, None]:
    test_database = os.getenv("TEST_PGDATABASE")
    if not test_database:
        pytest.skip("Set TEST_PGDATABASE to a dedicated test database")
    if test_database == os.getenv("PGDATABASE", "postgres"):
        pytest.fail("TEST_PGDATABASE must differ from the development database")

    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-secret")
    test_url = URL.create(
        "postgresql+psycopg",
        username=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        host=os.getenv("PGHOST", "127.0.0.1"),
        port=int(os.getenv("PGPORT", "5432")),
        database=test_database,
    )
    test_engine = create_engine(test_url)
    TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)
    Base.metadata.create_all(test_engine)

    def override_get_db() -> Generator[Session, None, None]:
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        with TestSession.begin() as session:
            session.execute(delete(User).where(User.email.like("auth-test-%")))
        app.dependency_overrides.clear()
        test_engine.dispose()


def register(client: TestClient, email: str):
    return client.post(
        "/auth/register",
        json={"email": email, "password": "Correct-Horse-123"},
    )


def login(client: TestClient, email: str) -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "Correct-Horse-123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def bearer(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_registration_hashes_password_and_rejects_duplicate(auth_client):
    email = f"auth-test-{uuid4()}@example.com"
    response = register(auth_client, email)

    assert response.status_code == 201
    assert response.json()["message"] == "Registration successful"
    assert response.json()["user"]["email"] == email
    assert response.json()["user"]["role"] == "student"

    duplicate = register(auth_client, email)
    assert duplicate.status_code == 409

    user_id = response.json()["user"]["id"]
    me = auth_client.get("/auth/users/" + str(user_id), headers=bearer(login(auth_client, email)))
    assert me.status_code == 200

    session_factory = app.dependency_overrides[get_db]
    session = next(session_factory())
    try:
        stored_user = session.get(User, user_id)
        assert stored_user.password_hash != "Correct-Horse-123"
        assert stored_user.password_hash.startswith("$2b$12$")
    finally:
        session.close()


def test_login_jwt_expiry_and_invalid_credentials(auth_client, monkeypatch):
    email = f"auth-test-{uuid4()}@example.com"
    register(auth_client, email)
    token = login(auth_client, email)
    payload = jwt.decode(token, "test-only-secret", algorithms=["HS256"])

    assert payload["email"] == email
    assert payload["role"] == "student"
    assert payload["exp"] - payload["iat"] == 60 * 60

    wrong_password = auth_client.post(
        "/auth/login", json={"email": email, "password": "Wrong-Password-123"}
    )
    unknown_email = auth_client.post(
        "/auth/login",
        json={"email": f"auth-test-{uuid4()}@example.com", "password": "Correct-Horse-123"},
    )
    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == {
        "detail": "Incorrect email or password"
    }


def test_logout_invalidates_token_and_private_profiles_are_protected(auth_client):
    first_email = f"auth-test-{uuid4()}@example.com"
    second_email = f"auth-test-{uuid4()}@example.com"
    first = register(auth_client, first_email).json()["user"]
    second = register(auth_client, second_email).json()["user"]
    first_token = login(auth_client, first_email)

    assert auth_client.get("/auth/me").status_code == 401
    assert auth_client.get("/auth/me", headers=bearer(first_token)).json()["id"] == first["id"]
    assert (
        auth_client.get(f"/auth/users/{second['id']}", headers=bearer(first_token)).status_code
        == 403
    )

    logged_out = auth_client.post("/auth/logout", headers=bearer(first_token))
    assert logged_out.status_code == 200
    assert auth_client.get("/auth/me", headers=bearer(first_token)).status_code == 401

    session_factory = app.dependency_overrides[get_db]
    session = next(session_factory())
    try:
        moderator_email = f"auth-test-{uuid4()}@example.com"
        session.add(
            User(
                email=moderator_email,
                password_hash=hash_password("Correct-Horse-123"),
                role=UserRole.MODERATOR,
            )
        )
        session.commit()
    finally:
        session.close()

    moderator_token = login(auth_client, moderator_email)
    moderator_response = auth_client.get(
        f"/auth/users/{second['id']}", headers=bearer(moderator_token)
    )
    assert moderator_response.status_code == 200
    assert moderator_response.json()["email"] == second_email
