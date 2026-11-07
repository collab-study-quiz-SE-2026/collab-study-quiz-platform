from test_quizzes import make_approved_question


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
    opened = client.patch(
        f"/quizzes/{response.json()['id']}/active-question",
        json={"position": 0},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert opened.status_code == 200
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


def test_host_can_sync_active_question_over_authenticated_websocket(test_setup):
    client, _, _, student_token, _, _, _, moderator_token = test_setup
    quiz, _ = create_quiz(client, student_token, moderator_token)

    with client.websocket_connect(f"/ws/quizzes/{quiz['id']}") as websocket:
        websocket.send_json({"type": "authenticate", "token": student_token})
        state = websocket.receive_json()
        assert state["event"] == "state"
        assert state["active_question_position"] == 0
        assert "room_code" not in state

        changed = client.patch(
            f"/quizzes/{quiz['id']}/active-question",
            json={"position": 0},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert changed.status_code == 200
        event = websocket.receive_json()
        assert event["event"] == "question_changed"
        assert event["active_question_position"] == 0


def test_only_quiz_host_can_select_active_question(test_setup):
    client, _, _, student_token, _, other_token, _, moderator_token = test_setup
    quiz, _ = create_quiz(client, student_token, moderator_token)
    response = client.patch(
        f"/quizzes/{quiz['id']}/active-question",
        json={"position": 0},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


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
