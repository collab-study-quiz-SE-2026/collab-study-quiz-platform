from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Question, QuestionStatus, User, UserRole


@pytest.fixture
def test_setup(monkeypatch) -> Generator[tuple[TestClient, sessionmaker, User, str, User, str], None, None]:
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

    with TestingSession() as session:
        student1 = User(
            email="student1@example.com",
            password_hash=hash_password("pass123"),
            role=UserRole.STUDENT,
        )
        student2 = User(
            email="student2@example.com",
            password_hash=hash_password("pass123"),
            role=UserRole.STUDENT,
        )
        moderator = User(
            email="moderator@example.com",
            password_hash=hash_password("modpass123"),
            role=UserRole.MODERATOR,
        )
        session.add_all([student1, student2, moderator])
        session.commit()
        session.refresh(student1)
        session.refresh(student2)
        session.refresh(moderator)

        token1 = create_access_token(student1)
        token2 = create_access_token(student2)
        mod_token = create_access_token(moderator)

    with TestClient(app) as client:
        yield client, TestingSession, student1, token1, student2, token2

    app.dependency_overrides.clear()


def make_question(client, token, subject="Computer Science", topic="Operating Systems", difficulty="medium", **overrides):
    payload = {
        "question_text": "Sample question text?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer_index": 0,
        "subject": subject,
        "topic": topic,
        "difficulty": difficulty,
        "explanation": "Sample explanation",
    }
    payload.update(overrides)
    response = client.post(
        "/questions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def test_question_assigned_subject_and_topic(test_setup):
    client, SessionLocal, student1, token1, _, _ = test_setup

    q = make_question(
        client,
        token1,
        subject="Distributed Systems",
        topic="Consensus",
        difficulty="hard",
    )

    assert q["subject"] == "Distributed Systems"
    assert q["topic"] == "Consensus"
    assert q["difficulty"] == "hard"

    with SessionLocal() as session:
        db_q = session.get(Question, q["id"])
        assert db_q is not None
        assert db_q.subject == "Distributed Systems"
        assert db_q.topic == "Consensus"
        assert db_q.difficulty == "hard"


def test_question_difficulty_classification(test_setup):
    client, _, student1, token1, _, _ = test_setup

    for diff in ["easy", "medium", "hard"]:
        q = make_question(client, token1, difficulty=diff)
        assert q["difficulty"] == diff

    # Invalid difficulty is rejected
    invalid_resp = client.post(
        "/questions",
        json={
            "question_text": "Invalid diff?",
            "options": ["A", "B", "C", "D"],
            "correct_answer_index": 0,
            "subject": "Math",
            "topic": "Algebra",
            "difficulty": "insane",
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert invalid_resp.status_code == 422


def test_students_filter_questions_by_category(test_setup):
    client, SessionLocal, student1, token1, _, _ = test_setup

    q_db_sql = make_question(
        client, token1,
        subject="Databases", topic="SQL", difficulty="easy",
        question_text="What does SELECT do?"
    )
    q_db_idx = make_question(
        client, token1,
        subject="Databases", topic="Indexing", difficulty="hard",
        question_text="What is a B-Tree?"
    )
    q_net_tcp = make_question(
        client, token1,
        subject="Networks", topic="TCP", difficulty="medium",
        question_text="What is TCP handshake?"
    )

    with SessionLocal() as session:
        for question_id in (q_db_sql["id"], q_db_idx["id"], q_net_tcp["id"]):
            session.get(Question, question_id).status = QuestionStatus.APPROVED
        session.commit()

    # 1. Filter by subject
    res_subj = client.get("/questions?subject=Databases")
    assert res_subj.status_code == 200
    ids_subj = [item["id"] for item in res_subj.json()]
    assert q_db_sql["id"] in ids_subj
    assert q_db_idx["id"] in ids_subj
    assert q_net_tcp["id"] not in ids_subj

    # 2. Filter by topic
    res_topic = client.get("/questions?topic=TCP")
    assert res_topic.status_code == 200
    ids_topic = [item["id"] for item in res_topic.json()]
    assert ids_topic == [q_net_tcp["id"]]

    # 3. Filter by difficulty
    res_diff = client.get("/questions?difficulty=hard")
    assert res_diff.status_code == 200
    ids_diff = [item["id"] for item in res_diff.json()]
    assert ids_diff == [q_db_idx["id"]]

    # 4. Multi-category filter: subject + difficulty
    res_multi = client.get("/questions?subject=Databases&difficulty=easy")
    assert res_multi.status_code == 200
    ids_multi = [item["id"] for item in res_multi.json()]
    assert ids_multi == [q_db_sql["id"]]

    # 5. Search endpoint by category (matches subject or topic)
    res_search = client.get("/questions/search?category=Databases")
    assert res_search.status_code == 200
    search_ids = [item["id"] for item in res_search.json()]
    assert q_db_sql["id"] in search_ids
    assert q_db_idx["id"] in search_ids
    assert q_net_tcp["id"] not in search_ids


def test_list_categories_summary(test_setup):
    client, SessionLocal, student1, token1, _, _ = test_setup

    physics = make_question(client, token1, subject="Physics", topic="Mechanics")
    math = make_question(client, token1, subject="Math", topic="Calculus")
    make_question(client, token1, subject="Pending Subject", topic="Pending Topic")

    with SessionLocal() as session:
        session.get(Question, physics["id"]).status = QuestionStatus.APPROVED
        session.get(Question, math["id"]).status = QuestionStatus.APPROVED
        session.commit()

    res = client.get("/questions/categories")
    assert res.status_code == 200
    data = res.json()
    assert "Physics" in data["subjects"]
    assert "Math" in data["subjects"]
    assert "Mechanics" in data["topics"]
    assert "Calculus" in data["topics"]
    assert "Pending Subject" not in data["subjects"]
    assert "Pending Topic" not in data["topics"]
    assert set(data["difficulties"]) == {"easy", "medium", "hard"}


def test_categorization_preserved_when_question_updated(test_setup):
    client, SessionLocal, student1, token1, _, _ = test_setup

    q = make_question(
        client,
        token1,
        subject="Cybersecurity",
        topic="Cryptography",
        difficulty="hard",
        question_text="What is AES?",
        explanation="AES is a symmetric cipher.",
    )
    q_id = q["id"]

    # Update only the question prompt and options without specifying subject, topic, or difficulty
    update_resp = client.patch(
        f"/questions/{q_id}",
        json={
            "question_text": "What does AES encryption stand for?",
            "options": ["Advanced Encryption Standard", "Automated Encryption System", "Applied Encrypted Secret", "Asymmetric Entry Service"],
        },
        headers={"Authorization": f"Bearer {token1}"},
    )

    assert update_resp.status_code == 200
    updated = update_resp.json()

    # Content changed
    assert updated["question_text"] == "What does AES encryption stand for?"
    assert updated["options"][0] == "Advanced Encryption Standard"

    # Categorization is preserved
    assert updated["subject"] == "Cybersecurity"
    assert updated["topic"] == "Cryptography"
    assert updated["difficulty"] == "hard"

    # Confirm in DB
    with SessionLocal() as session:
        db_q = session.get(Question, q_id)
        assert db_q.subject == "Cybersecurity"
        assert db_q.topic == "Cryptography"
        assert db_q.difficulty == "hard"


def test_categorization_can_be_explicitly_updated(test_setup):
    client, _, student1, token1, _, _ = test_setup

    q = make_question(
        client, token1,
        subject="Math", topic="Algebra", difficulty="easy"
    )

    # Explicitly update subject and difficulty
    res = client.patch(
        f"/questions/{q['id']}",
        json={
            "subject": "Advanced Mathematics",
            "difficulty": "medium",
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["subject"] == "Advanced Mathematics"
    assert data["topic"] == "Algebra"  # Unchanged
    assert data["difficulty"] == "medium"


def test_unauthorized_student_cannot_update_foreign_question(test_setup):
    client, _, student1, token1, student2, token2 = test_setup

    q = make_question(client, token1, question_text="Student 1's question")

    # Student 2 attempts to update Student 1's question
    res = client.patch(
        f"/questions/{q['id']}",
        json={"question_text": "Hacked prompt"},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "You can only update your own questions"
