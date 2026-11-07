from test_participation import create_quiz


def test_student_can_retrieve_completed_attempt_history(test_setup):
    client, _, _, student_token, _, _, _, moderator_token = test_setup
    quiz, question_id = create_quiz(client, student_token, moderator_token)
    started = client.post(
        f"/quizzes/{quiz['id']}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()
    client.post(
        f"/quiz-sessions/{started['id']}/answers",
        json={"question_id": question_id, "answer_index": 2, "time_spent_seconds": 11},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    client.post(
        f"/quiz-sessions/{started['id']}/complete",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    response = client.get(
        "/quiz-attempts/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    assert response.json()[0]["quiz_title"] == "Participation"
    assert response.json()[0]["score"] == 100
    assert response.json()[0]["answers"] == {str(question_id): 2}
    assert response.json()[0]["question_timings"] == {str(question_id): 11}
    assert response.json()[0]["completed_at"] is not None

    trends = client.get(
        "/quiz-attempts/me/trends",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert trends.status_code == 200
    assert trends.json()["completed_attempts"] == 1
    assert trends.json()["average_score"] == 100
    assert trends.json()["best_score"] == 100
    assert len(trends.json()["daily_average_scores"]) == 1


def test_attempt_history_is_private_to_the_authenticated_student(test_setup):
    client, _, _, student_token, other_student, other_token, _, moderator_token = test_setup
    quiz, _ = create_quiz(client, student_token, moderator_token)
    started = client.post(
        f"/quizzes/{quiz['id']}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()
    client.post(
        f"/quiz-sessions/{started['id']}/complete",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert client.get(
        f"/users/{other_student.id}/quiz-attempts",
        headers={"Authorization": f"Bearer {student_token}"},
    ).status_code == 403
    own = client.get(
        f"/users/{other_student.id}/quiz-attempts",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert own.status_code == 200
    assert own.json() == []
