from fastapi import WebSocketDisconnect
import pytest

from app import main
from app.models import QuizAttempt
from test_quizzes import make_approved_question


def make_live_quiz(client, host_token, moderator_token):
    question_id = make_approved_question(
        client, host_token, moderator_token, "Which option is correct live?"
    )
    response = client.post(
        "/quizzes",
        json={
            "title": "Live round",
            "duration_minutes": 10,
            "question_ids": [question_id],
        },
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert response.status_code == 201
    return response.json(), question_id


def connect_quiz(client, room_code, token):
    return client.websocket_connect(
        f"/ws/quizzes/{room_code}",
        subprotocols=["csmqp.v1", f"bearer.{token}"],
    )


def test_live_round_broadcasts_question_and_withholds_key_until_all_answer(test_setup, monkeypatch):
    client, testing_session, _, host_token, student, student_token, moderator, moderator_token = test_setup
    monkeypatch.setattr(main, "SessionLocal", testing_session)
    main.rooms.clear()
    quiz, question_id = make_live_quiz(client, host_token, moderator_token)
    for user, token in ((student, student_token), (moderator, moderator_token)):
        joined = client.post(
            f"/quizzes/{quiz['id']}/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert joined.status_code == 200

    with (
        connect_quiz(client, quiz["room_code"], host_token) as host,
        connect_quiz(client, quiz["room_code"], student_token) as first,
        connect_quiz(client, quiz["room_code"], moderator_token) as second,
    ):
        assert host.receive_json()["role"] == "host"
        assert first.receive_json()["role"] == "participant"
        assert second.receive_json()["role"] == "participant"
        first.send_text("not JSON")
        assert first.receive_json() == {
            "type": "ERROR",
            "message": "Message must be valid JSON",
        }

        host.send_json({"type": "START_QUIZ"})
        host_question = host.receive_json()
        first_question = first.receive_json()
        second_question = second.receive_json()
        assert host_question == first_question == second_question
        assert host_question["type"] == "QUESTION_OPEN"
        assert host_question["question_id"] == question_id
        assert host_question["duration_seconds"] == 30
        assert "correct_answer_index" not in host_question
        assert "explanation" not in host_question
        assert main.rooms[quiz["id"]]["last_broadcast_ms"] < 150

        first.send_json(
            {"type": "SUBMIT_ANSWER", "question_id": question_id, "answer_index": 2}
        )
        assert first.receive_json()["type"] == "ANSWER_STATE"
        assert host.receive_json()["type"] == "ANSWER_STATE"
        assert second.receive_json()["type"] == "ANSWER_STATE"
        assert main.rooms[quiz["id"]]["round_started"] is True

        second.send_json(
            {"type": "SUBMIT_ANSWER", "question_id": question_id, "answer_index": 0}
        )
        first.receive_json()
        host.receive_json()
        second.receive_json()
        first_result = first.receive_json()
        host_result = host.receive_json()
        second_result = second.receive_json()
        assert first_result == host_result == second_result
        assert first_result["type"] == "ROUND_END"
        assert first_result["correct_answer_index"] == 2
        assert first_result["explanation"] == "Private explanation"
        assert first_result["quiz_complete"] is True
        assert len(first_result["standings"]) == 2

    with testing_session() as session:
        attempts = session.query(QuizAttempt).filter_by(quiz_id=quiz["id"]).all()
        assert {attempt.status.value for attempt in attempts} == {"completed"}


def test_live_round_ends_when_timer_expires_and_handles_invalid_event(test_setup, monkeypatch):
    client, testing_session, _, host_token, student, student_token, _, moderator_token = test_setup
    monkeypatch.setattr(main, "SessionLocal", testing_session)
    monkeypatch.setattr(main, "ROUND_SECONDS", 0.2)
    main.rooms.clear()
    quiz, question_id = make_live_quiz(client, host_token, moderator_token)
    joined = client.post(
        f"/quizzes/{quiz['id']}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert joined.status_code == 200

    with (
        connect_quiz(client, quiz["room_code"], host_token) as host,
        connect_quiz(client, quiz["room_code"], student_token) as participant,
    ):
        host.receive_json()
        participant.receive_json()
        host.send_json({"type": "START_QUIZ"})
        assert host.receive_json()["type"] == "QUESTION_OPEN"
        assert participant.receive_json()["type"] == "QUESTION_OPEN"
        participant.send_json({"type": "START_QUIZ"})
        assert participant.receive_json() == {
            "type": "ERROR",
            "message": "Only the quiz host can start a round",
        }
        host_result = host.receive_json()
        participant_result = participant.receive_json()
        assert host_result == participant_result
        assert host_result["type"] == "ROUND_END"
        assert host_result["correct_answer_index"] == 2
        assert host_result["standings"][0]["correct_answers"] == 0


def test_participant_can_reconnect_to_an_active_round(test_setup, monkeypatch):
    client, testing_session, _, host_token, _, student_token, _, moderator_token = test_setup
    monkeypatch.setattr(main, "SessionLocal", testing_session)
    main.rooms.clear()
    quiz, question_id = make_live_quiz(client, host_token, moderator_token)
    joined = client.post(
        f"/quizzes/{quiz['id']}/sessions",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert joined.status_code == 200

    with connect_quiz(client, quiz["room_code"], host_token) as host:
        host.receive_json()
        with connect_quiz(client, quiz["room_code"], student_token) as participant:
            participant.receive_json()
            host.send_json({"type": "START_QUIZ"})
            host.receive_json()
            participant.receive_json()

        with connect_quiz(client, quiz["room_code"], student_token) as reconnect:
            assert reconnect.receive_json()["role"] == "participant"
            reopened_question = reconnect.receive_json()
            assert reopened_question["type"] == "QUESTION_OPEN"
            assert reopened_question["question_id"] == question_id
            reconnect.send_json(
                {
                    "type": "SUBMIT_ANSWER",
                    "question_id": question_id,
                    "answer_index": 2,
                }
            )
            assert reconnect.receive_json()["type"] == "ANSWER_STATE"
            host.receive_json()
            assert reconnect.receive_json()["type"] == "ROUND_END"
            assert host.receive_json()["type"] == "ROUND_END"


def test_quiz_websocket_requires_a_valid_token(test_setup):
    client, *_ = test_setup
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/quizzes/UNKNOWN"):
            pass
