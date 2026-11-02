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
def test_setup(monkeypatch) -> Generator[tuple[TestClient, sessionmaker, User, str, User, str, User, str], None, None]:
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

        t1 = create_access_token(student1)
        t2 = create_access_token(student2)
        tm = create_access_token(moderator)

    with TestClient(app) as client:
        yield client, TestingSession, student1, t1, student2, t2, moderator, tm

    app.dependency_overrides.clear()


def make_question(client, token, **overrides):
    payload = {
        "question_text": "Original Question Text?",
        "options": ["A", "B", "C", "D"],
        "correct_answer_index": 0,
        "subject": "Computer Science",
        "topic": "Algorithms",
        "difficulty": "easy",
        "explanation": "Original explanation",
    }
    payload.update(overrides)
    response = client.post(
        "/questions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def test_students_view_available_questions(test_setup):
    client, _, student1, t1, _, _, _, _ = test_setup

    q = make_question(client, t1, question_text="What is quicksort?")

    # 1. View available questions in public list
    list_resp = client.get("/questions")
    assert list_resp.status_code == 200
    ids = [item["id"] for item in list_resp.json()]
    assert q["id"] in ids

    # 2. View specific question details
    single_resp = client.get(f"/questions/{q['id']}")
    assert single_resp.status_code == 200
    assert single_resp.json()["question_text"] == "What is quicksort?"


def test_students_view_their_own_contributed_questions(test_setup):
    client, _, student1, t1, student2, t2, _, _ = test_setup

    q1 = make_question(client, t1, question_text="Author question 1")
    q2 = make_question(client, t1, question_text="Author question 2")
    q_other = make_question(client, t2, question_text="Other student question")

    # Author requests their own questions
    resp = client.get(
        "/questions/me",
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert resp.status_code == 200
    my_ids = [item["id"] for item in resp.json()]
    assert q1["id"] in my_ids
    assert q2["id"] in my_ids
    assert q_other["id"] not in my_ids


def test_creators_edit_their_own_questions(test_setup):
    client, _, student1, t1, student2, t2, _, _ = test_setup

    q = make_question(
        client, t1,
        question_text="Initial typo in question?",
        explanation="Initial explanation"
    )

    # Creator successfully edits the question
    update_resp = client.patch(
        f"/questions/{q['id']}",
        json={
            "question_text": "Corrected question text?",
            "explanation": "Refined explanation",
        },
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["question_text"] == "Corrected question text?"
    assert data["explanation"] == "Refined explanation"

    # Other student cannot edit author's question
    forbidden_resp = client.patch(
        f"/questions/{q['id']}",
        json={"question_text": "Malicious modification"},
        headers={"Authorization": f"Bearer {t2}"},
    )
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()["detail"] == "You can only update your own questions"


def test_changes_saved_and_reflected_in_question_bank(test_setup):
    client, SessionLocal, student1, t1, _, _, _, _ = test_setup

    q = make_question(client, t1, question_text="Before edit")

    # Perform edit
    client.patch(
        f"/questions/{q['id']}",
        json={"question_text": "After edit - completely reflected"},
        headers={"Authorization": f"Bearer {t1}"},
    )

    # 1. Reflected in single question lookup
    single_res = client.get(f"/questions/{q['id']}")
    assert single_res.status_code == 200
    assert single_res.json()["question_text"] == "After edit - completely reflected"

    # 2. Reflected in database
    with SessionLocal() as session:
        stored = session.get(Question, q["id"])
        assert stored.question_text == "After edit - completely reflected"


def test_editing_rejected_question_resets_to_pending_for_review(test_setup):
    client, _, student1, t1, _, _, _, tm = test_setup

    q = make_question(client, t1, question_text="Question with mistake")

    # Moderator rejects the question
    client.post(
        f"/questions/{q['id']}/reject?comment=Fix typo",
        headers={"Authorization": f"Bearer {tm}"},
    )

    # Creator fixes the mistake
    edit_resp = client.patch(
        f"/questions/{q['id']}",
        json={"question_text": "Question with typo fixed"},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert edit_resp.status_code == 200
    # Status reset to pending for re-moderation
    assert edit_resp.json()["status"] == "pending"
    assert edit_resp.json()["moderator_id"] is None
    assert edit_resp.json()["moderation_comment"] is None


def test_authorized_users_can_delete_questions(test_setup):
    client, SessionLocal, student1, t1, student2, t2, moderator, tm = test_setup

    q1 = make_question(client, t1, question_text="Delete by author")
    q2 = make_question(client, t1, question_text="Delete by moderator")

    # 1. Unauthorized student cannot delete author's question
    forbid_del = client.delete(
        f"/questions/{q1['id']}",
        headers={"Authorization": f"Bearer {t2}"},
    )
    assert forbid_del.status_code == 403
    assert forbid_del.json()["detail"] == "You can only delete your own questions"

    # 2. Unauthenticated request cannot delete
    unauth_del = client.delete(f"/questions/{q1['id']}")
    assert unauth_del.status_code == 401

    # 3. Creator deletes their own question
    del_res1 = client.delete(
        f"/questions/{q1['id']}",
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert del_res1.status_code == 200
    assert del_res1.json()["message"] == "Question deleted successfully"

    # Confirm deletion reflected in question bank
    assert client.get(f"/questions/{q1['id']}").status_code == 404
    with SessionLocal() as session:
        assert session.get(Question, q1["id"]) is None

    # 4. Moderator can delete any question
    del_res2 = client.delete(
        f"/questions/{q2['id']}",
        headers={"Authorization": f"Bearer {tm}"},
    )
    assert del_res2.status_code == 200
    assert client.get(f"/questions/{q2['id']}").status_code == 404


def test_delete_nonexistent_question(test_setup):
    client, _, student1, t1, _, _, _, _ = test_setup

    res = client.delete(
        "/questions/999999",
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Question not found"
