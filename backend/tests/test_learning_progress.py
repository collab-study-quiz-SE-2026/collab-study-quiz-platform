def make_question_for_progress(
    client,
    token,
    moderator_token,
    text,
    subject="Computer Science",
    topic="Algorithms",
    correct_answer_index=2,
):
    response = client.post(
        "/questions",
        json={
            "question_text": text,
            "options": ["A", "B", "C", "D"],
            "correct_answer_index": correct_answer_index,
            "subject": subject,
            "topic": topic,
            "difficulty": "medium",
            "explanation": "Explanation",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    question_id = response.json()["id"]
    client.post(
        f"/questions/{question_id}/approve",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    return question_id


def test_learning_progress_empty_state_when_no_quizzes_completed(test_setup):
    client, _, _, student_token, _, _, _, _ = test_setup

    response = client.get(
        "/analytics/progress",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_quizzes_completed"] == 0
    assert data["average_score"] is None
    assert data["highest_score"] is None
    assert data["lowest_score"] is None
    assert data["initial_score"] is None
    assert data["latest_score"] is None
    assert data["overall_improvement"] is None
    assert data["trend_direction"] == "insufficient_data"
    assert data["timeline"] == []
    assert data["topic_trends"] == []


def test_learning_progress_chronological_trend_and_trajectory(test_setup):
    client, _, _, student_token, _, _, _, moderator_token = test_setup

    q1 = make_question_for_progress(
        client, student_token, moderator_token,
        text="Question 1", topic="Sorting", correct_answer_index=2
    )
    q2 = make_question_for_progress(
        client, student_token, moderator_token,
        text="Question 2", topic="Sorting", correct_answer_index=1
    )

    # Create 3 quizzes
    quizzes = []
    for title in ["Quiz Alpha", "Quiz Beta", "Quiz Gamma"]:
        q_res = client.post(
            "/quizzes",
            json={"title": title, "duration_minutes": 15, "question_ids": [q1, q2]},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert q_res.status_code == 201
        quizzes.append(q_res.json())

    # Quiz 1: Score 50% (1/2 correct)
    s1 = client.post(f"/quizzes/{quizzes[0]['id']}/sessions", headers={"Authorization": f"Bearer {student_token}"}).json()
    client.post(f"/quiz-sessions/{s1['id']}/answers", json={"question_id": q1, "answer_index": 2, "time_spent_seconds": 10}, headers={"Authorization": f"Bearer {student_token}"})
    client.post(f"/quiz-sessions/{s1['id']}/answers", json={"question_id": q2, "answer_index": 0, "time_spent_seconds": 15}, headers={"Authorization": f"Bearer {student_token}"})
    client.post(f"/quiz-sessions/{s1['id']}/complete", headers={"Authorization": f"Bearer {student_token}"})

    # Quiz 2: Score 100% (2/2 correct)
    s2 = client.post(f"/quizzes/{quizzes[1]['id']}/sessions", headers={"Authorization": f"Bearer {student_token}"}).json()
    client.post(f"/quiz-sessions/{s2['id']}/answers", json={"question_id": q1, "answer_index": 2, "time_spent_seconds": 8}, headers={"Authorization": f"Bearer {student_token}"})
    client.post(f"/quiz-sessions/{s2['id']}/answers", json={"question_id": q2, "answer_index": 1, "time_spent_seconds": 12}, headers={"Authorization": f"Bearer {student_token}"})
    client.post(f"/quiz-sessions/{s2['id']}/complete", headers={"Authorization": f"Bearer {student_token}"})

    # Quiz 3: Score 50% (1/2 correct)
    s3 = client.post(f"/quizzes/{quizzes[2]['id']}/sessions", headers={"Authorization": f"Bearer {student_token}"}).json()
    client.post(f"/quiz-sessions/{s3['id']}/answers", json={"question_id": q1, "answer_index": 2, "time_spent_seconds": 9}, headers={"Authorization": f"Bearer {student_token}"})
    client.post(f"/quiz-sessions/{s3['id']}/answers", json={"question_id": q2, "answer_index": 3, "time_spent_seconds": 14}, headers={"Authorization": f"Bearer {student_token}"})
    client.post(f"/quiz-sessions/{s3['id']}/complete", headers={"Authorization": f"Bearer {student_token}"})

    # Retrieve learning progress
    res = client.get(
        "/analytics/progress",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["total_quizzes_completed"] == 3
    assert data["highest_score"] == 100
    assert data["lowest_score"] == 50
    assert data["initial_score"] == 50
    assert data["latest_score"] == 50
    assert data["overall_improvement"] == 0.0
    assert data["trend_direction"] == "stable"

    timeline = data["timeline"]
    assert len(timeline) == 3

    # Point 1
    assert timeline[0]["quiz_title"] == "Quiz Alpha"
    assert timeline[0]["score"] == 50
    assert timeline[0]["moving_average_score"] == 50.0
    assert timeline[0]["trajectory"] == "stable"

    # Point 2
    assert timeline[1]["quiz_title"] == "Quiz Beta"
    assert timeline[1]["score"] == 100
    assert timeline[1]["moving_average_score"] == 75.0
    assert timeline[1]["trajectory"] == "improving"

    # Point 3
    assert timeline[2]["quiz_title"] == "Quiz Gamma"
    assert timeline[2]["score"] == 50
    assert timeline[2]["moving_average_score"] == 66.67
    assert timeline[2]["trajectory"] == "declining"

    # Topic trend
    assert len(data["topic_trends"]) == 1
    topic_info = data["topic_trends"][0]
    assert topic_info["topic"] == "Sorting"
    assert topic_info["total_attempts"] == 3
    assert len(topic_info["history"]) == 3


def test_learning_progress_access_controls(test_setup):
    client, _, _, student_token, other_student, other_token, _, moderator_token = test_setup

    # Student cannot view another student's progress
    forbidden = client.get(
        f"/users/{other_student.id}/analytics/progress",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert forbidden.status_code == 403
    assert "own learning progress" in forbidden.json()["detail"]

    # Moderator CAN view another student's progress
    allowed = client.get(
        f"/users/{other_student.id}/analytics/progress",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["student_id"] == other_student.id

    # Non-existent user returns 404
    not_found = client.get(
        "/users/88888/analytics/progress",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert not_found.status_code == 404


def test_active_attempt_is_excluded_from_progress_until_completed(test_setup):
    client, _, _, student_token, _, _, _, moderator_token = test_setup

    q = make_question_for_progress(
        client, student_token, moderator_token,
        text="Sample Question", topic="Networks"
    )
    quiz_res = client.post(
        "/quizzes",
        json={"title": "Networks Quiz", "duration_minutes": 10, "question_ids": [q]},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    quiz_id = quiz_res.json()["id"]

    # Start session but don't complete
    session = client.post(
        f"/quizzes/{quiz_id}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()

    res_before = client.get("/analytics/progress", headers={"Authorization": f"Bearer {student_token}"})
    assert res_before.status_code == 200
    assert res_before.json()["total_quizzes_completed"] == 0

    # Complete session
    client.post(
        f"/quiz-sessions/{session['id']}/answers",
        json={"question_id": q, "answer_index": 2, "time_spent_seconds": 6},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    client.post(f"/quiz-sessions/{session['id']}/complete", headers={"Authorization": f"Bearer {student_token}"})

    res_after = client.get("/analytics/progress", headers={"Authorization": f"Bearer {student_token}"})
    assert res_after.status_code == 200
    assert res_after.json()["total_quizzes_completed"] == 1
    assert res_after.json()["timeline"][0]["score"] == 100
