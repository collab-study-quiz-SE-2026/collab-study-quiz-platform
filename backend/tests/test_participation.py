from test_quizzes import make_approved_question
from app.models import QuizAttempt


def create_quiz(client, student_token, moderator_token):
    question_id = make_approved_question(
        client, student_token, moderator_token, "Which option is correct?"
    )
    response = client.post(
        "/quizzes",
        json={"title": "Participation", "duration_minutes": 30, "question_ids": [question_id]},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 201
    return response.json(), question_id


def test_student_joins_by_room_submits_answer_and_is_scored(test_setup):
    client, _, _, student_token, _, _, _, moderator_token = test_setup
    quiz, question_id = create_quiz(client, student_token, moderator_token)

    joined = client.post(
        f"/quizzes/join/{quiz['room_code'].lower()}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert joined.status_code == 200
    attempt = joined.json()
    assert attempt["status"] == "active"

    answer = client.post(
        f"/quiz-sessions/{attempt['id']}/answers",
        json={"question_id": question_id, "answer_index": 2, "time_spent_seconds": 8},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert answer.status_code == 200
    completed = client.post(
        f"/quiz-sessions/{attempt['id']}/complete",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["score"] == 100
    assert completed.json()["accuracy"] == 100
    assert completed.json()["correct_answers"] == 1
    assert completed.json()["incorrect_answers"] == 0


def test_attempt_reports_accuracy_and_withholds_answer_keys(test_setup):
    client, _, _, student_token, _, _, _, moderator_token = test_setup
    first_question = make_approved_question(
        client, student_token, moderator_token, "First scoring question?"
    )
    second_question = make_approved_question(
        client, student_token, moderator_token, "Second scoring question?"
    )
    quiz_response = client.post(
        "/quizzes",
        json={
            "title": "Scoring checks",
            "duration_minutes": 30,
            "question_ids": [first_question, second_question],
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert quiz_response.status_code == 201

    attempt = client.post(
        f"/quizzes/{quiz_response.json()['id']}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()
    assert attempt["accuracy"] is None
    for question in attempt["questions"]:
        assert "correct_answer_index" not in question
        assert "explanation" not in question

    for question_id, answer_index in ((first_question, 2), (second_question, 0)):
        submitted = client.post(
            f"/quiz-sessions/{attempt['id']}/answers",
            json={
                "question_id": question_id,
                "answer_index": answer_index,
                "time_spent_seconds": 5,
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert submitted.status_code == 200
        assert submitted.json()["accuracy"] is None

    completed = client.post(
        f"/quiz-sessions/{attempt['id']}/complete",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert completed.status_code == 200
    assert completed.json()["score"] == 50
    assert completed.json()["accuracy"] == 50
    assert completed.json()["correct_answers"] == 1
    assert completed.json()["incorrect_answers"] == 1
    for question in completed.json()["questions"]:
        assert "correct_answer_index" not in question
        assert "explanation" not in question


def test_expired_attempt_is_scored_from_submitted_answers(test_setup, monkeypatch):
    client, testing_session, _, student_token, _, _, _, moderator_token = test_setup
    quiz, question_id = create_quiz(client, student_token, moderator_token)
    attempt = client.post(
        f"/quizzes/{quiz['id']}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()
    answer = client.post(
        f"/quiz-sessions/{attempt['id']}/answers",
        json={"question_id": question_id, "answer_index": 2, "time_spent_seconds": 8},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert answer.status_code == 200

    monkeypatch.setattr("app.main.attempt_expired", lambda *_: True)
    expired = client.post(
        f"/quiz-sessions/{attempt['id']}/complete",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert expired.status_code == 200
    assert expired.json()["status"] == "expired"
    assert expired.json()["score"] == 100
    assert expired.json()["accuracy"] == 100
    assert expired.json()["correct_answers"] == 1
    assert expired.json()["incorrect_answers"] == 0

    with testing_session() as session:
        saved_attempt = session.get(QuizAttempt, attempt["id"])
        assert saved_attempt is not None
        assert saved_attempt.correct_answer_count == 1


def test_students_cannot_submit_to_another_students_session(test_setup):
    client, _, _, student_token, other_student, other_token, _, moderator_token = test_setup
    quiz, question_id = create_quiz(client, student_token, moderator_token)
    joined = client.post(
        f"/quizzes/{quiz['id']}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    attempt_id = joined.json()["id"]
    forbidden = client.post(
        f"/quiz-sessions/{attempt_id}/answers",
        json={"question_id": question_id, "answer_index": 0, "time_spent_seconds": 1},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert forbidden.status_code == 403


def test_invalid_room_is_rejected_and_max_attempts_are_enforced(test_setup):
    client, _, _, student_token, _, _, _, moderator_token = test_setup
    assert client.post(
        "/quizzes/join/NOPE99", headers={"Authorization": f"Bearer {student_token}"}
    ).status_code == 404
    quiz, _ = create_quiz(client, student_token, moderator_token)
    joined = client.post(
        f"/quizzes/{quiz['id']}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    client.post(
        f"/quiz-sessions/{joined.json()['id']}/complete",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert client.post(
        f"/quizzes/{quiz['id']}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    ).status_code == 409
