import pytest
from pydantic import ValidationError

from app.schemas import QuizCreate


def valid_quiz():
    return {
        "title": "DBMS Basics",
        "description": "A short practice quiz",
        "duration_minutes": 20,
        "question_ids": [1, 2, 3],
        "max_attempts": 1,
    }


def test_valid_quiz():
    quiz = QuizCreate(**valid_quiz())
    assert quiz.title == "DBMS Basics"
    assert quiz.question_ids == [1, 2, 3]


def test_default_max_attempts():
    data = valid_quiz()
    del data["max_attempts"]
    assert QuizCreate(**data).max_attempts == 1


@pytest.mark.parametrize("bad_title", ["", "   "])
def test_blank_title_rejected(bad_title):
    data = valid_quiz()
    data["title"] = bad_title
    with pytest.raises(ValidationError):
        QuizCreate(**data)


@pytest.mark.parametrize("duration", [0, -5, 181])
def test_bad_duration_rejected(duration):
    data = valid_quiz()
    data["duration_minutes"] = duration
    with pytest.raises(ValidationError):
        QuizCreate(**data)


@pytest.mark.parametrize("ids", [[], [0], [-2], [1, 1]])
def test_bad_question_ids_rejected(ids):
    data = valid_quiz()
    data["question_ids"] = ids
    with pytest.raises(ValidationError):
        QuizCreate(**data)


@pytest.mark.parametrize("attempts", [0, -1, 11])
def test_bad_attempt_count_rejected(attempts):
    data = valid_quiz()
    data["max_attempts"] = attempts
    with pytest.raises(ValidationError):
        QuizCreate(**data)


def test_title_is_trimmed():
    data = valid_quiz()
    data["title"] = "  DBMS Basics  "
    assert QuizCreate(**data).title == "DBMS Basics"


def test_very_long_title_rejected():
    data = valid_quiz()
    data["title"] = "x" * 201
    with pytest.raises(ValidationError):
        QuizCreate(**data)
