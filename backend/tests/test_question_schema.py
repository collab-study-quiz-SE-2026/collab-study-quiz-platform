import pytest
from pydantic import ValidationError

from app.schemas.questions import QuestionCreate


def valid_question(**overrides):
    question = {
        "question_text": "What is a primary key?",
        "options": ["Unique ID", "Index", "View", "Join"],
        "correct_answer_index": 0,
        "topic": "DBMS",
        "difficulty": "easy",
    }
    question.update(overrides)
    return question


def test_accepts_valid_question():
    question = QuestionCreate(**valid_question())

    assert question.question_text == "What is a primary key?"
    assert question.options == ["Unique ID", "Index", "View", "Join"]
    assert question.correct_answer_index == 0
    assert question.topic == "DBMS"
    assert question.difficulty == "easy"


@pytest.mark.parametrize("question_text", ["", "   "])
def test_rejects_blank_question_text(question_text):
    with pytest.raises(ValidationError):
        QuestionCreate(**valid_question(question_text=question_text))


@pytest.mark.parametrize("correct_answer_index", [-1, 4, 5])
def test_rejects_out_of_range_correct_answer(correct_answer_index):
    with pytest.raises(ValidationError):
        QuestionCreate(**valid_question(correct_answer_index=correct_answer_index))


def test_rejects_wrong_number_of_options():
    with pytest.raises(ValidationError):
        QuestionCreate(**valid_question(options=["A", "B", "C"]))


def test_rejects_blank_option():
    with pytest.raises(ValidationError):
        QuestionCreate(**valid_question(options=["A", " ", "C", "D"]))


def test_rejects_unknown_difficulty():
    with pytest.raises(ValidationError):
        QuestionCreate(**valid_question(difficulty="expert"))
