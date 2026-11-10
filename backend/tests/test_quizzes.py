from app.models import QuestionStatus


def make_approved_question(client, token, moderator_token, text):
    response = client.post(
        "/questions",
        json={
            "question_text": text,
            "options": ["A", "B", "C", "D"],
            "correct_answer_index": 2,
            "subject": "Computer Science",
            "topic": "Testing",
            "difficulty": "easy",
            "explanation": "Private explanation",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    question_id = response.json()["id"]
    approved = client.post(
        f"/questions/{question_id}/approve",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert approved.status_code == 200
    return question_id


def test_authenticated_host_creates_quiz_with_approved_questions_without_answer_keys(test_setup):
    client, _, _, student_token, _, _, _, moderator_token = test_setup
    question_id = make_approved_question(
        client, student_token, moderator_token, "What should be tested?"
    )

    response = client.post(
        "/quizzes",
        json={
            "title": "Testing Basics",
            "description": "Practice",
            "duration_minutes": 15,
            "question_ids": [question_id],
            "max_attempts": 2,
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 201
    quiz = response.json()
    assert len(quiz["room_code"]) == 6
    assert quiz["questions"][0]["id"] == question_id
    assert "correct_answer_index" not in quiz["questions"][0]
    assert "explanation" not in quiz["questions"][0]


def test_quiz_creation_requires_approved_existing_questions(test_setup):
    client, _, _, student_token, _, _, _, _ = test_setup
    response = client.post(
        "/quizzes",
        json={
            "title": "Invalid",
            "duration_minutes": 15,
            "question_ids": [99999],
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 422


def test_quiz_creation_requires_authentication(test_setup):
    client, *_ = test_setup
    response = client.post(
        "/quizzes",
        json={"title": "No auth", "duration_minutes": 15, "question_ids": [1]},
    )
    assert response.status_code == 401
