from test_participation import create_quiz


def complete_attempt(client, token, quiz_id, question_id, answer_index, timing):
    started = client.post(
        f"/quizzes/{quiz_id}/sessions",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    client.post(
        f"/quiz-sessions/{started['id']}/answers",
        json={
            "question_id": question_id,
            "answer_index": answer_index,
            "time_spent_seconds": timing,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    response = client.post(
        f"/quiz-sessions/{started['id']}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_performance_dashboard_reports_attempt_metrics_and_trends(test_setup):
    client, _, _, student_token, _, _, _, moderator_token = test_setup
    quiz, question_id = create_quiz(client, student_token, moderator_token)
    complete_attempt(client, student_token, quiz["id"], question_id, 2, 12)

    response = client.get(
        "/dashboard/performance",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    dashboard = response.json()
    assert dashboard["total_quizzes_attempted"] == 1
    assert dashboard["average_score"] == 100
    assert dashboard["average_time_per_question_seconds"] == 12
    assert dashboard["cohort_percentile"] == 100
    assert dashboard["topic_accuracy"] == [
        {
            "topic": "Testing",
            "answered_questions": 1,
            "correct_answers": 1,
            "accuracy_percentage": 100,
        }
    ]
    assert len(dashboard["recent_results"]) == 1
    assert len(dashboard["trend"]) == 1


def test_dashboard_has_an_empty_state_and_private_access(test_setup):
    client, _, _, student_token, other_student, other_token, _, _ = test_setup
    empty = client.get(
        "/dashboard/performance",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert empty.status_code == 200
    assert empty.json()["total_quizzes_attempted"] == 0
    assert empty.json()["average_score"] is None
    assert empty.json()["topic_accuracy"] == []

    forbidden = client.get(
        f"/users/{other_student.id}/dashboard/performance",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert forbidden.status_code == 403
