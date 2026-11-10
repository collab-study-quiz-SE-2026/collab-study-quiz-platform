from app.models import AttemptStatus, QuizAttempt


def make_custom_question(
    client,
    token,
    moderator_token,
    text,
    subject="Computer Science",
    topic="Testing",
    correct_answer_index=2,
):
    response = client.post(
        "/questions",
        json={
            "question_text": text,
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer_index": correct_answer_index,
            "subject": subject,
            "topic": topic,
            "difficulty": "medium",
            "explanation": "Detailed explanation",
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


def test_topic_performance_empty_state_for_new_student(test_setup):
    client, _, _, student_token, _, _, _, _ = test_setup

    response = client.get(
        "/analytics/topics",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_quizzes_evaluated"] == 0
    assert data["total_questions_evaluated"] == 0
    assert data["topics"] == []
    assert data["strong_topics"] == []
    assert data["weak_topics"] == []


def test_topic_performance_calculates_accuracy_timing_and_strength(test_setup):
    client, _, _, student_token, _, _, _, moderator_token = test_setup

    # Create questions in two distinct topics
    q1 = make_custom_question(
        client, student_token, moderator_token,
        text="What is unit testing?",
        subject="Software Engineering",
        topic="Testing",
        correct_answer_index=2,
    )
    q2 = make_custom_question(
        client, student_token, moderator_token,
        text="What is quicksort complexity?",
        subject="Computer Science",
        topic="Algorithms",
        correct_answer_index=1,
    )

    # Create quiz
    quiz_res = client.post(
        "/quizzes",
        json={
            "title": "SE & CS Assessment",
            "duration_minutes": 20,
            "question_ids": [q1, q2],
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert quiz_res.status_code == 201
    quiz_id = quiz_res.json()["id"]

    # Start session
    session_res = client.post(
        f"/quizzes/{quiz_id}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert session_res.status_code == 200
    session_id = session_res.json()["id"]

    # Submit answers: q1 correct with 12s, q2 incorrect with 28s
    ans1 = client.post(
        f"/quiz-sessions/{session_id}/answers",
        json={"question_id": q1, "answer_index": 2, "time_spent_seconds": 12},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert ans1.status_code == 200

    ans2 = client.post(
        f"/quiz-sessions/{session_id}/answers",
        json={"question_id": q2, "answer_index": 3, "time_spent_seconds": 28},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert ans2.status_code == 200

    # Active attempt is not yet counted in analytics
    uncompleted = client.get(
        "/analytics/topics",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert uncompleted.status_code == 200
    assert uncompleted.json()["total_quizzes_evaluated"] == 0

    # Complete the attempt
    complete_res = client.post(
        f"/quiz-sessions/{session_id}/complete",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert complete_res.status_code == 200

    # Now verify topic analytics
    response = client.get(
        "/analytics/topics",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_quizzes_evaluated"] == 1
    assert data["total_questions_evaluated"] == 2
    assert "Testing" in data["strong_topics"]
    assert "Algorithms" in data["weak_topics"]

    topic_map = {item["topic"]: item for item in data["topics"]}
    assert "Testing" in topic_map
    assert topic_map["Testing"]["subject"] == "Software Engineering"
    assert topic_map["Testing"]["total_questions"] == 1
    assert topic_map["Testing"]["correct_answers"] == 1
    assert topic_map["Testing"]["accuracy_percentage"] == 100.0
    assert topic_map["Testing"]["average_time_seconds"] == 12.0
    assert topic_map["Testing"]["strength_level"] == "strong"

    assert "Algorithms" in topic_map
    assert topic_map["Algorithms"]["subject"] == "Computer Science"
    assert topic_map["Algorithms"]["total_questions"] == 1
    assert topic_map["Algorithms"]["correct_answers"] == 0
    assert topic_map["Algorithms"]["accuracy_percentage"] == 0.0
    assert topic_map["Algorithms"]["average_time_seconds"] == 28.0
    assert topic_map["Algorithms"]["strength_level"] == "weak"


def test_topic_performance_cohort_percentile_calculation(test_setup):
    client, _, _, student_token, other_student, other_token, _, moderator_token = test_setup

    q = make_custom_question(
        client, student_token, moderator_token,
        text="What is a binary search tree?",
        subject="Computer Science",
        topic="Data Structures",
        correct_answer_index=2,
    )

    quiz_res = client.post(
        "/quizzes",
        json={"title": "Data Structures Quiz", "duration_minutes": 15, "question_ids": [q]},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    quiz_id = quiz_res.json()["id"]

    # Student 1 scores 100%
    s1 = client.post(
        f"/quizzes/{quiz_id}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()
    client.post(
        f"/quiz-sessions/{s1['id']}/answers",
        json={"question_id": q, "answer_index": 2, "time_spent_seconds": 10},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    client.post(
        f"/quiz-sessions/{s1['id']}/complete",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Student 2 scores 0%
    s2 = client.post(
        f"/quizzes/{quiz_id}/sessions",
        headers={"Authorization": f"Bearer {other_token}"},
    ).json()
    client.post(
        f"/quiz-sessions/{s2['id']}/answers",
        json={"question_id": q, "answer_index": 0, "time_spent_seconds": 20},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    client.post(
        f"/quiz-sessions/{s2['id']}/complete",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    # Verify Student 1 percentile (100.0%)
    res1 = client.get(
        "/analytics/topics",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res1.status_code == 200
    topic_data_1 = res1.json()["topics"][0]
    assert topic_data_1["cohort_percentile"] == 100.0

    # Verify Student 2 percentile (50.0%)
    res2 = client.get(
        "/analytics/topics",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert res2.status_code == 200
    topic_data_2 = res2.json()["topics"][0]
    assert topic_data_2["cohort_percentile"] == 50.0


def test_topic_performance_subject_filter(test_setup):
    client, _, _, student_token, _, _, _, moderator_token = test_setup

    q_math = make_custom_question(
        client, student_token, moderator_token,
        text="2 + 2 = ?",
        subject="Mathematics",
        topic="Arithmetic",
        correct_answer_index=2,
    )
    q_cs = make_custom_question(
        client, student_token, moderator_token,
        text="What is RAM?",
        subject="Hardware",
        topic="Memory",
        correct_answer_index=2,
    )

    quiz_res = client.post(
        "/quizzes",
        json={"title": "Mixed Quiz", "duration_minutes": 15, "question_ids": [q_math, q_cs]},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    quiz_id = quiz_res.json()["id"]

    session = client.post(
        f"/quizzes/{quiz_id}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()
    client.post(
        f"/quiz-sessions/{session['id']}/answers",
        json={"question_id": q_math, "answer_index": 2, "time_spent_seconds": 5},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    client.post(
        f"/quiz-sessions/{session['id']}/answers",
        json={"question_id": q_cs, "answer_index": 2, "time_spent_seconds": 15},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    client.post(
        f"/quiz-sessions/{session['id']}/complete",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Filter by Mathematics
    res_filtered = client.get(
        "/analytics/topics?subject=Mathematics",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res_filtered.status_code == 200
    data_filtered = res_filtered.json()
    assert len(data_filtered["topics"]) == 1
    assert data_filtered["topics"][0]["subject"] == "Mathematics"
    assert data_filtered["topics"][0]["topic"] == "Arithmetic"


def test_topic_performance_access_control_and_privacy(test_setup):
    client, _, _, student_token, other_student, other_token, _, moderator_token = test_setup

    # Other student cannot access student's analytics
    forbidden = client.get(
        f"/users/{other_student.id}/analytics/topics",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert forbidden.status_code == 403
    assert "own topic performance" in forbidden.json()["detail"]

    # Moderator CAN access other student's analytics
    moderator_access = client.get(
        f"/users/{other_student.id}/analytics/topics",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert moderator_access.status_code == 200
    assert moderator_access.json()["student_id"] == other_student.id

    # Non-existent user returns 404
    not_found = client.get(
        "/users/999999/analytics/topics",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert not_found.status_code == 404
