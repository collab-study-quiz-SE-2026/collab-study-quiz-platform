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
        # Create student user
        student = User(
            email="student@example.com",
            password_hash=hash_password("studentpass123"),
            role=UserRole.STUDENT,
        )
        # Create moderator user
        moderator = User(
            email="moderator@example.com",
            password_hash=hash_password("modpass123"),
            role=UserRole.MODERATOR,
        )
        session.add_all([student, moderator])
        session.commit()
        session.refresh(student)
        session.refresh(moderator)

        student_token = create_access_token(student)
        moderator_token = create_access_token(moderator)

    with TestClient(app) as client:
        yield client, TestingSession, student, student_token, moderator, moderator_token

    app.dependency_overrides.clear()


def question_payload(**overrides):
    payload = {
        "question_text": "What is normalization in DBMS?",
        "options": ["Decomposing tables", "Adding triggers", "Creating indexes", "Exporting logs"],
        "correct_answer_index": 0,
        "topic": "DBMS",
        "difficulty": "medium",
        "explanation": "Normalization minimizes data redundancy and avoids update anomalies.",
    }
    payload.update(overrides)
    return payload


def test_moderator_reviews_submitted_questions(test_setup):
    client, _, student, student_token, moderator, moderator_token = test_setup

    # Student submits two questions
    q1 = client.post(
        "/questions",
        json=question_payload(question_text="Q1 for review"),
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    q2 = client.post(
        "/questions",
        json=question_payload(question_text="Q2 for review"),
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    # Moderator accesses review queue
    response = client.get(
        "/moderation/questions",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )

    assert response.status_code == 200
    items = response.json()
    ids = [item["id"] for item in items]
    assert q1["id"] in ids
    assert q2["id"] in ids
    assert all(item["status"] == "pending" for item in items)


def test_moderator_approves_question(test_setup):
    client, SessionLocal, student, student_token, moderator, moderator_token = test_setup

    q = client.post(
        "/questions",
        json=question_payload(question_text="Valid question to approve"),
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    # Moderate to approved
    response = client.patch(
        f"/questions/{q['id']}/moderate",
        json={"status": "approved", "comment": "Good quality question."},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["moderator_id"] == moderator.id
    assert data["moderation_comment"] == "Good quality question."
    assert data["moderated_at"] is not None

    # Check persistence in database
    with SessionLocal() as session:
        stored = session.get(Question, q["id"])
        assert stored.status == QuestionStatus.APPROVED
        assert stored.moderator_id == moderator.id


def test_moderator_rejects_question(test_setup):
    client, SessionLocal, student, student_token, moderator, moderator_token = test_setup

    q = client.post(
        "/questions",
        json=question_payload(question_text="Low quality question to reject"),
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    # Moderate to rejected
    response = client.patch(
        f"/questions/{q['id']}/moderate",
        json={"action": "reject", "comment": "Vague question prompt."},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["moderator_id"] == moderator.id
    assert data["moderation_comment"] == "Vague question prompt."

    # Verify persistence
    with SessionLocal() as session:
        stored = session.get(Question, q["id"])
        assert stored.status == QuestionStatus.REJECTED


def test_convenience_approve_and_reject_endpoints(test_setup):
    client, _, _, student_token, _, moderator_token = test_setup

    q1 = client.post(
        "/questions",
        json=question_payload(question_text="Approve via shortcut"),
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    q2 = client.post(
        "/questions",
        json=question_payload(question_text="Reject via shortcut"),
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    # POST /questions/{id}/approve
    resp_app = client.post(
        f"/questions/{q1['id']}/approve",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert resp_app.status_code == 200
    assert resp_app.json()["status"] == "approved"

    # POST /questions/{id}/reject
    resp_rej = client.post(
        f"/questions/{q2['id']}/reject?comment=Inappropriate",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert resp_rej.status_code == 200
    assert resp_rej.json()["status"] == "rejected"
    assert resp_rej.json()["moderation_comment"] == "Inappropriate"


def test_rejected_questions_excluded_from_published_sets(test_setup):
    client, _, _, student_token, _, moderator_token = test_setup

    # Create 3 questions
    q_good = client.post(
        "/questions",
        json=question_payload(question_text="Good question", topic="Algorithms"),
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    q_bad = client.post(
        "/questions",
        json=question_payload(question_text="Bad question", topic="Algorithms"),
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    # Moderator approves q_good and rejects q_bad
    client.post(
        f"/questions/{q_good['id']}/approve",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    client.post(
        f"/questions/{q_bad['id']}/reject",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )

    # 1. Query /questions list: rejected question MUST be excluded
    list_resp = client.get("/questions?topic=Algorithms")
    assert list_resp.status_code == 200
    returned_ids = [item["id"] for item in list_resp.json()]
    assert q_good["id"] in returned_ids
    assert q_bad["id"] not in returned_ids, "Rejected question must not appear in published list"

    # 2. Search /questions/search: rejected question MUST be excluded
    search_resp = client.get("/questions/search?topic=Algorithms")
    assert search_resp.status_code == 200
    search_ids = [item["id"] for item in search_resp.json()]
    assert q_good["id"] in search_ids
    assert q_bad["id"] not in search_ids, "Rejected question must not appear in search results"

    # A rejected question must not be available through direct lookup either.
    rejected_detail = client.get(f"/questions/{q_bad['id']}")
    assert rejected_detail.status_code == 404


def test_pending_questions_are_hidden_from_public_endpoints(test_setup):
    client, _, _, student_token, _, _ = test_setup

    pending = client.post(
        "/questions",
        json=question_payload(question_text="Still waiting for review"),
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    # Public lists and searches return only approved questions, even if a caller
    # tries to request pending questions with an extra query parameter.
    assert client.get("/questions").json() == []
    assert client.get("/questions?status_filter=pending").json() == []
    assert client.get("/questions/search").json() == []
    assert client.get("/questions/search?status_filter=pending").json() == []

    # A pending question cannot be fetched directly by its ID.
    response = client.get(f"/questions/{pending['id']}")
    assert response.status_code == 404


def test_unauthorized_users_cannot_perform_moderation(test_setup):
    client, _, student, student_token, _, _ = test_setup

    q = client.post(
        "/questions",
        json=question_payload(question_text="Moderation auth test question"),
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    # 1. Unauthenticated requests rejected with 401
    resp_noauth_list = client.get("/moderation/questions")
    assert resp_noauth_list.status_code == 401

    resp_noauth_mod = client.patch(
        f"/questions/{q['id']}/moderate",
        json={"status": "approved"},
    )
    assert resp_noauth_mod.status_code == 401

    # 2. Student (non-moderator) requests rejected with 403 Forbidden
    resp_student_list = client.get(
        "/moderation/questions",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp_student_list.status_code == 403
    assert resp_student_list.json()["detail"] == "Moderator privileges required"

    resp_student_mod = client.patch(
        f"/questions/{q['id']}/moderate",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp_student_mod.status_code == 403
    assert resp_student_mod.json()["detail"] == "Moderator privileges required"

    resp_student_app = client.post(
        f"/questions/{q['id']}/approve",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp_student_app.status_code == 403

    resp_student_rej = client.post(
        f"/questions/{q['id']}/reject",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp_student_rej.status_code == 403


def test_moderate_nonexistent_question(test_setup):
    client, _, _, _, _, moderator_token = test_setup

    response = client.patch(
        "/questions/999999/moderate",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Question not found"


def test_moderate_invalid_decision_payload(test_setup):
    client, _, _, student_token, _, moderator_token = test_setup

    q = client.post(
        "/questions",
        json=question_payload(),
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    response = client.patch(
        f"/questions/{q['id']}/moderate",
        json={"comment": "No decision provided"},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert response.status_code == 422
