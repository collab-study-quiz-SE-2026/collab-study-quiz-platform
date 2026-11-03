from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Question, User, UserRole


@pytest.fixture
def test_setup(monkeypatch) -> Generator[tuple[TestClient, sessionmaker, User, str], None, None]:
    monkeypatch.setenv("JWT_SECRET_KEY", "testing-jwt-secret-key-for-test-suite-12345")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    # Create a default student user and token
    with TestingSession() as session:
        student = User(
            email="student@example.com",
            password_hash=hash_password("password123"),
            role=UserRole.STUDENT,
        )
        session.add(student)
        session.commit()
        session.refresh(student)
        token = create_access_token(student)

    with TestClient(app) as client:
        yield client, TestingSession, student, token

    app.dependency_overrides.clear()


def valid_payload(**overrides):
    payload = {
        "question_text": "What is a primary key?",
        "options": ["Unique ID", "Foreign Key", "Index", "Trigger"],
        "correct_answer_index": 0,
        "topic": "DBMS",
        "difficulty": "easy",
        "explanation": "A primary key uniquely identifies each record in a relational table.",
    }
    payload.update(overrides)
    return payload


def test_authenticated_student_creates_question(test_setup):
    client, SessionLocal, student, token = test_setup

    response = client.post(
        "/questions",
        json=valid_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["question_text"] == "What is a primary key?"
    assert data["options"] == ["Unique ID", "Foreign Key", "Index", "Trigger"]
    assert data["correct_answer_index"] == 0
    assert data["topic"] == "DBMS"
    assert data["difficulty"] == "easy"
    assert data["explanation"] == "A primary key uniquely identifies each record in a relational table."
    assert data["creator_id"] == student.id
    assert "created_at" in data

    # Verify database persistence
    with SessionLocal() as session:
        stored = session.get(Question, data["id"])
        assert stored is not None
        assert stored.question_text == "What is a primary key?"
        assert stored.creator_id == student.id


def test_create_question_requires_authentication(test_setup):
    client, _, _, _ = test_setup

    # Without Authorization header
    response = client.post("/questions", json=valid_payload())
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"

    # With invalid token
    response = client.post(
        "/questions",
        json=valid_payload(),
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401


@pytest.mark.parametrize("question_text", ["", "   "])
def test_rejects_blank_question_text(test_setup, question_text):
    client, _, _, token = test_setup

    response = client.post(
        "/questions",
        json=valid_payload(question_text=question_text),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("topic", ["", "   "])
def test_rejects_blank_topic(test_setup, topic):
    client, _, _, token = test_setup

    response = client.post(
        "/questions",
        json=valid_payload(topic=topic),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("options", [
    ["A", "B", "C"],              # Only 3 options
    ["A", "B", "C", "D", "E"],    # 5 options
    ["A", "   ", "C", "D"],       # Blank option
])
def test_rejects_invalid_options(test_setup, options):
    client, _, _, token = test_setup

    response = client.post(
        "/questions",
        json=valid_payload(options=options),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("correct_index", [-1, 4, 10])
def test_rejects_out_of_bounds_correct_answer(test_setup, correct_index):
    client, _, _, token = test_setup

    response = client.post(
        "/questions",
        json=valid_payload(correct_answer_index=correct_index),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_rejects_invalid_difficulty(test_setup):
    client, _, _, token = test_setup

    response = client.post(
        "/questions",
        json=valid_payload(difficulty="impossible"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_retrieve_questions_list_and_by_id(test_setup):
    client, _, _, token = test_setup

    # Create two questions
    q1_resp = client.post(
        "/questions",
        json=valid_payload(question_text="Question 1", topic="DBMS"),
        headers={"Authorization": f"Bearer {token}"},
    )
    q2_resp = client.post(
        "/questions",
        json=valid_payload(question_text="Question 2", topic="OS"),
        headers={"Authorization": f"Bearer {token}"},
    )
    q1_id = q1_resp.json()["id"]
    q2_id = q2_resp.json()["id"]

    # List all questions
    list_resp = client.get("/questions")
    assert list_resp.status_code == 200
    ids = [item["id"] for item in list_resp.json()]
    assert q1_id in ids
    assert q2_id in ids

    # Retrieve single question by ID
    single_resp = client.get(f"/questions/{q1_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["question_text"] == "Question 1"

    # Non-existent ID returns 404
    missing_resp = client.get("/questions/999999")
    assert missing_resp.status_code == 404
    assert missing_resp.json()["detail"] == "Question not found"


def test_filter_and_search_questions_by_topic(test_setup):
    client, _, _, token = test_setup

    client.post(
        "/questions",
        json=valid_payload(question_text="What is TCP?", topic="Networks"),
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/questions",
        json=valid_payload(question_text="What is a page fault?", topic="OS"),
        headers={"Authorization": f"Bearer {token}"},
    )

    # Filter with query param topic
    resp = client.get("/questions?topic=Networks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["topic"] == "Networks"
    assert data[0]["question_text"] == "What is TCP?"

    # Search endpoint with topic
    search_resp = client.get("/questions/search?topic=OS")
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert len(search_data) == 1
    assert search_data[0]["topic"] == "OS"


def test_sql_injection_defense_on_search(test_setup):
    client, _, _, token = test_setup

    client.post(
        "/questions",
        json=valid_payload(question_text="Normal Question", topic="Math"),
        headers={"Authorization": f"Bearer {token}"},
    )

    malicious_query = "' OR '1'='1'; DROP TABLE questions; --"
    resp = client.get(f"/questions?topic={malicious_query}")
    assert resp.status_code == 200
    assert resp.json() == []

    # Verify table and existing records are intact
    all_resp = client.get("/questions")
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 1
