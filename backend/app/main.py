from datetime import UTC, datetime, timedelta
import os
from contextlib import closing

import psycopg
import jwt
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth import JWT_ALGORITHM, create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import (
    AttemptStatus,
    Question,
    QuestionStatus,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    QuizStatus,
    User,
    UserRole,
)
from app.schemas import (
    CategorySummaryResponse,
    LoginRequest,
    MessageResponse,
    ModerateQuestionRequest,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    AnswerSubmission,
    ActivateQuizQuestionRequest,
    QuizCreate,
    QuizAttemptResponse,
    QuizAttemptHistoryResponse,
    QuizAttemptTrendResponse,
    QuizPublicResponse,
    QuizResponse,
    RegistrationRequest,
    RegistrationResponse,
    TokenResponse,
    UserResponse,
)
from app.storage import get_storage_client

app = FastAPI()
frontend_origins = [origin.strip() for origin in os.getenv(
    "FRONTEND_ORIGIN", "http://localhost:5173,https://localhost"
).split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

quiz_connections: dict[int, set[WebSocket]] = {}


def quiz_response(quiz: Quiz) -> dict:
    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "duration_minutes": quiz.duration_minutes,
        "max_attempts": quiz.max_attempts,
        "room_code": quiz.room_code,
        "status": quiz.status,
        "host_id": quiz.host_id,
        "created_at": quiz.created_at,
        "started_at": quiz.started_at,
        "active_question_position": quiz.active_question_position,
        "questions": [
            {
                "id": link.question.id,
                "question_text": link.question.question_text,
                "options": link.question.options,
                "subject": link.question.subject,
                "topic": link.question.topic,
                "difficulty": link.question.difficulty,
            }
            for link in quiz.questions
        ],
    }


def public_quiz_response(quiz: Quiz) -> dict:
    response = quiz_response(quiz)
    response.pop("room_code")
    return response


async def broadcast_quiz_event(quiz_id: int, event: dict) -> None:
    connections = quiz_connections.get(quiz_id, set()).copy()
    for connection in connections:
        try:
            await connection.send_json(event)
        except (RuntimeError, WebSocketDisconnect):
            quiz_connections.get(quiz_id, set()).discard(connection)


def generate_room_code(db: Session) -> str:
    import secrets
    import string

    alphabet = string.ascii_uppercase + string.digits
    for _ in range(10):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        if db.scalar(select(Quiz).where(Quiz.room_code == code)) is None:
            return code
    raise HTTPException(status_code=503, detail="Could not allocate a quiz room")


def attempt_response(attempt: QuizAttempt) -> dict:
    return {
        "id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "student_id": attempt.student_id,
        "status": attempt.status,
        "score": attempt.score,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "answered_question_ids": [int(question_id) for question_id in attempt.answers],
        "question_timings": attempt.question_timings,
        "questions": [
            {
                "id": link.question.id,
                "question_text": link.question.question_text,
                "options": link.question.options,
                "subject": link.question.subject,
                "topic": link.question.topic,
                "difficulty": link.question.difficulty,
            }
            for link in attempt.quiz.questions
        ],
    }


def load_quiz(db: Session, quiz_id: int) -> Quiz | None:
    return db.scalar(
        select(Quiz)
        .options(selectinload(Quiz.questions).selectinload(QuizQuestion.question))
        .where(Quiz.id == quiz_id)
    )


def active_attempt(db: Session, quiz_id: int, student_id: int) -> QuizAttempt | None:
    return db.scalar(
        select(QuizAttempt)
        .options(selectinload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(QuizQuestion.question))
        .where(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.student_id == student_id,
            QuizAttempt.status == AttemptStatus.ACTIVE,
        )
    )


def attempt_expired(attempt: QuizAttempt, now: datetime) -> bool:
    started_at = attempt.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    return now > started_at + timedelta(minutes=attempt.quiz.duration_minutes)


def require_moderator(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.MODERATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator privileges required",
        )
    return current_user


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def database_health():
    try:
        with psycopg.connect(connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Database unavailable") from None

    return {"status": "ok", "database": "connected"}


@app.get("/health/storage")
def storage_health():
    try:
        with closing(get_storage_client()) as client:
            client.head_bucket(Bucket=os.environ["S3_BUCKET"])
    except (BotoCoreError, ClientError, KeyError):
        raise HTTPException(status_code=503, detail="Storage unavailable") from None
    return {"status": "ok", "storage": "connected"}


@app.post(
    "/auth/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(details: RegistrationRequest, db: Session = Depends(get_db)):
    email = str(details.email).lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(email=email, password_hash=hash_password(details.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Registration successful", "user": user}


@app.post("/auth/login", response_model=TokenResponse)
def login(details: LoginRequest, db: Session = Depends(get_db)):
    email = str(details.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(details.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return {"access_token": create_access_token(user), "token_type": "bearer"}


@app.post("/auth/logout", response_model=MessageResponse)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.token_version += 1
    db.commit()
    return {"message": "Logged out successfully"}


@app.get("/auth/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/quizzes", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
@app.post(
    "/api/v1/quizzes",
    response_model=QuizResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_quiz(
    details: QuizCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    questions = list(
        db.scalars(
            select(Question).where(
                Question.id.in_(details.question_ids),
                Question.status == QuestionStatus.APPROVED,
            )
        ).all()
    )
    questions_by_id = {question.id: question for question in questions}
    missing_ids = [question_id for question_id in details.question_ids if question_id not in questions_by_id]
    if missing_ids:
        raise HTTPException(
            status_code=422,
            detail=f"Approved questions not found: {missing_ids}",
        )

    quiz = Quiz(
        title=details.title,
        description=details.description,
        duration_minutes=details.duration_minutes,
        max_attempts=details.max_attempts,
        room_code=generate_room_code(db),
        status=QuizStatus.PUBLISHED,
        host_id=current_user.id,
        active_question_position=None,
    )
    quiz.questions = [
        QuizQuestion(question=questions_by_id[question_id], position=position)
        for position, question_id in enumerate(details.question_ids)
    ]
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz_response(quiz)


@app.get("/quizzes/{quiz_id}", response_model=QuizPublicResponse)
@app.get(
    "/api/v1/quizzes/{quiz_id}",
    response_model=QuizPublicResponse,
    include_in_schema=False,
)
def read_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = db.scalar(
        select(Quiz)
        .options(selectinload(Quiz.questions).selectinload(QuizQuestion.question))
        .where(Quiz.id == quiz_id)
    )
    if quiz is None or quiz.status == QuizStatus.DRAFT:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return public_quiz_response(quiz)


@app.get("/quizzes", response_model=list[QuizPublicResponse])
@app.get("/api/v1/quizzes", response_model=list[QuizPublicResponse], include_in_schema=False)
def list_quizzes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quizzes = db.scalars(
        select(Quiz)
        .options(selectinload(Quiz.questions).selectinload(QuizQuestion.question))
        .where(Quiz.status.in_([QuizStatus.PUBLISHED, QuizStatus.LIVE]))
        .order_by(Quiz.created_at.desc(), Quiz.id.desc())
    ).all()
    return [public_quiz_response(quiz) for quiz in quizzes]


def start_attempt(
    quiz: Quiz,
    current_user: User,
    db: Session,
) -> dict:
    now = datetime.now(UTC)
    # Lock the quiz row while checking attempts so parallel join requests
    # cannot both pass the maximum-attempt check.
    quiz = db.scalar(select(Quiz).where(Quiz.id == quiz.id).with_for_update())
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if quiz.status not in (QuizStatus.PUBLISHED, QuizStatus.LIVE):
        raise HTTPException(status_code=409, detail="Quiz is not available")
    existing = active_attempt(db, quiz.id, current_user.id)
    if existing is not None:
        if not attempt_expired(existing, now):
            return attempt_response(existing)
        existing.status = AttemptStatus.EXPIRED
        existing.score = 0
        existing.completed_at = now
        db.flush()
    count = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz.id,
        QuizAttempt.student_id == current_user.id,
        QuizAttempt.status.in_([AttemptStatus.COMPLETED, AttemptStatus.EXPIRED]),
    ).count()
    if count >= quiz.max_attempts:
        db.commit()
        raise HTTPException(status_code=409, detail="Maximum quiz attempts reached")
    attempt = QuizAttempt(quiz=quiz, student=current_user, started_at=now)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt_response(attempt)


@app.patch("/quizzes/{quiz_id}/active-question", response_model=QuizPublicResponse)
@app.patch(
    "/api/v1/quizzes/{quiz_id}/active-question",
    response_model=QuizPublicResponse,
    include_in_schema=False,
)
async def set_active_question(
    quiz_id: int,
    selection: ActivateQuizQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = load_quiz(db, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if quiz.host_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the quiz host can change the active question")
    if selection.position >= len(quiz.questions):
        raise HTTPException(status_code=422, detail="Question position is invalid")

    quiz.active_question_position = selection.position
    if quiz.status == QuizStatus.PUBLISHED:
        quiz.status = QuizStatus.LIVE
        quiz.started_at = datetime.now(UTC)
    db.commit()
    db.refresh(quiz)
    state = public_quiz_response(quiz)
    await broadcast_quiz_event(quiz.id, {"event": "question_changed", **state})
    return state


@app.post("/quizzes/{quiz_id}/sessions", response_model=QuizAttemptResponse)
@app.post(
    "/api/v1/quizzes/{quiz_id}/sessions",
    response_model=QuizAttemptResponse,
    include_in_schema=False,
)
def join_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = load_quiz(db, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return start_attempt(quiz, current_user, db)


@app.post("/quizzes/join/{room_code}", response_model=QuizAttemptResponse)
@app.post(
    "/api/v1/quizzes/join/{room_code}",
    response_model=QuizAttemptResponse,
    include_in_schema=False,
)
def join_quiz_by_room(
    room_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = db.scalar(select(Quiz).where(Quiz.room_code == room_code.upper()))
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz room not found")
    quiz = load_quiz(db, quiz.id)
    return start_attempt(quiz, current_user, db)


@app.post("/quiz-sessions/{attempt_id}/answers", response_model=QuizAttemptResponse)
@app.post(
    "/api/v1/quiz-sessions/{attempt_id}/answers",
    response_model=QuizAttemptResponse,
    include_in_schema=False,
)
async def submit_answer(
    attempt_id: int,
    answer: AnswerSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = db.scalar(
        select(QuizAttempt)
        .options(selectinload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(QuizQuestion.question))
        .where(QuizAttempt.id == attempt_id)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    if attempt.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only submit answers to your own session")
    if attempt.status != AttemptStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Quiz session is no longer active")
    now = datetime.now(UTC)
    if attempt_expired(attempt, now):
        attempt.status = AttemptStatus.EXPIRED
        attempt.score = 0
        attempt.completed_at = now
        db.commit()
        raise HTTPException(status_code=409, detail="Quiz time limit has expired")
    selected = next(
        (link.question for link in attempt.quiz.questions if link.question.id == answer.question_id),
        None,
    )
    if selected is None:
        raise HTTPException(status_code=422, detail="Question is not part of this quiz")
    if attempt.quiz.active_question_position is None:
        raise HTTPException(status_code=409, detail="The host has not opened a question yet")
    active_question = attempt.quiz.questions[attempt.quiz.active_question_position].question
    if selected.id != active_question.id:
        raise HTTPException(status_code=409, detail="This question is not currently active")
    if answer.answer_index >= len(selected.options):
        raise HTTPException(status_code=422, detail="Answer index is invalid")
    attempt.answers = {**attempt.answers, str(answer.question_id): answer.answer_index}
    attempt.question_timings = {
        **attempt.question_timings,
        str(answer.question_id): answer.time_spent_seconds,
    }
    db.commit()
    db.refresh(attempt)
    await broadcast_quiz_event(
        attempt.quiz_id,
        {
            "event": "answer_submitted",
            "attempt_id": attempt.id,
            "question_id": answer.question_id,
            "answered_question_ids": [int(question_id) for question_id in attempt.answers],
        },
    )
    return attempt_response(attempt)


@app.post("/quiz-sessions/{attempt_id}/complete", response_model=QuizAttemptResponse)
@app.post(
    "/api/v1/quiz-sessions/{attempt_id}/complete",
    response_model=QuizAttemptResponse,
    include_in_schema=False,
)
async def complete_quiz(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = db.scalar(
        select(QuizAttempt)
        .options(selectinload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(QuizQuestion.question))
        .where(QuizAttempt.id == attempt_id)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    if attempt.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only complete your own session")
    if attempt.status != AttemptStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Quiz session is no longer active")
    now = datetime.now(UTC)
    if attempt_expired(attempt, now):
        attempt.status = AttemptStatus.EXPIRED
        score = 0
    else:
        correct = sum(
            int(str(link.question.id) in attempt.answers
                and attempt.answers[str(link.question.id)] == link.question.correct_answer_index)
            for link in attempt.quiz.questions
        )
        score = round(correct * 100 / len(attempt.quiz.questions))
        attempt.status = AttemptStatus.COMPLETED
    attempt.score = score
    attempt.completed_at = now
    db.commit()
    db.refresh(attempt)
    await broadcast_quiz_event(
        attempt.quiz_id,
        {"event": "attempt_completed", "attempt_id": attempt.id, "status": attempt.status},
    )
    return attempt_response(attempt)


def attempt_history_response(attempt: QuizAttempt) -> dict:
    duration_seconds = None
    if attempt.completed_at is not None:
        started_at = attempt.started_at
        completed_at = attempt.completed_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=UTC)
        duration_seconds = max(0, round((completed_at - started_at).total_seconds()))
    return {
        "id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "quiz_title": attempt.quiz.title,
        "student_id": attempt.student_id,
        "status": attempt.status,
        "score": attempt.score,
        "answers": attempt.answers,
        "question_timings": attempt.question_timings,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "duration_seconds": duration_seconds,
    }


@app.get("/quiz-attempts/me", response_model=list[QuizAttemptHistoryResponse])
@app.get(
    "/api/v1/quiz-attempts/me",
    response_model=list[QuizAttemptHistoryResponse],
    include_in_schema=False,
)
def list_my_attempt_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempts = db.scalars(
        select(QuizAttempt)
        .options(selectinload(QuizAttempt.quiz))
        .where(
            QuizAttempt.student_id == current_user.id,
            QuizAttempt.status.in_([AttemptStatus.COMPLETED, AttemptStatus.EXPIRED]),
        )
        .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc())
    ).all()
    return [attempt_history_response(attempt) for attempt in attempts]


@app.get("/quiz-attempts/me/trends", response_model=QuizAttemptTrendResponse)
@app.get(
    "/api/v1/quiz-attempts/me/trends",
    response_model=QuizAttemptTrendResponse,
    include_in_schema=False,
)
def my_attempt_trends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempts = db.scalars(
        select(QuizAttempt)
        .where(
            QuizAttempt.student_id == current_user.id,
            QuizAttempt.status == AttemptStatus.COMPLETED,
            QuizAttempt.score.is_not(None),
        )
        .order_by(QuizAttempt.completed_at, QuizAttempt.id)
    ).all()
    daily_scores: dict[str, list[int]] = {}
    for attempt in attempts:
        if attempt.completed_at is not None and attempt.score is not None:
            day = attempt.completed_at.date().isoformat()
            daily_scores.setdefault(day, []).append(attempt.score)

    return {
        "completed_attempts": len(attempts),
        "average_score": (
            round(sum(attempt.score for attempt in attempts if attempt.score is not None) / len(attempts), 2)
            if attempts
            else None
        ),
        "best_score": max((attempt.score for attempt in attempts if attempt.score is not None), default=None),
        "daily_average_scores": [
            {"date": day, "average_score": round(sum(scores) / len(scores), 2)}
            for day, scores in sorted(daily_scores.items())
        ],
    }


@app.get("/users/{student_id}/quiz-attempts", response_model=list[QuizAttemptHistoryResponse])
@app.get(
    "/api/v1/users/{student_id}/quiz-attempts",
    response_model=list[QuizAttemptHistoryResponse],
    include_in_schema=False,
)
def list_student_attempt_history(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id != student_id:
        raise HTTPException(status_code=403, detail="You can only access your own attempt history")
    return list_my_attempt_history(current_user=current_user, db=db)


@app.get("/auth/users/{user_id}", response_model=UserResponse)
def read_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id != user_id and current_user.role != UserRole.MODERATOR:
        raise HTTPException(status_code=403, detail="You can only access your own account")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post(
    "/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
@app.post(
    "/api/v1/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_question(
    details: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question = Question(
        question_text=details.question_text,
        options=details.options,
        correct_answer_index=details.correct_answer_index,
        subject=details.subject,
        topic=details.topic,
        difficulty=details.difficulty,
        explanation=details.explanation,
        creator_id=current_user.id,
        status=QuestionStatus.PENDING,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@app.get("/questions/me", response_model=list[QuestionResponse])
@app.get("/questions/my", response_model=list[QuestionResponse], include_in_schema=False)
@app.get("/api/v1/questions/me", response_model=list[QuestionResponse], include_in_schema=False)
def list_my_questions(
    subject: str | None = None,
    topic: str | None = None,
    status_filter: QuestionStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """View questions contributed by the currently authenticated student."""
    stmt = select(Question).where(Question.creator_id == current_user.id)
    if status_filter:
        stmt = stmt.where(Question.status == status_filter)
    if subject:
        stmt = stmt.where(Question.subject == subject)
    if topic:
        stmt = stmt.where(Question.topic == topic)
    stmt = stmt.order_by(Question.created_at.desc(), Question.id.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


@app.get("/questions/categories", response_model=CategorySummaryResponse)
@app.get(
    "/api/v1/questions/categories",
    response_model=CategorySummaryResponse,
    include_in_schema=False,
)
def list_categories(db: Session = Depends(get_db)):
    """Return distinct subjects, topics, and difficulty levels in the question bank."""
    subjects = list(
        db.scalars(
            select(Question.subject)
            .where(Question.status == QuestionStatus.APPROVED)
            .distinct()
        ).all()
    )
    topics = list(
        db.scalars(
            select(Question.topic)
            .where(Question.status == QuestionStatus.APPROVED)
            .distinct()
        ).all()
    )
    return CategorySummaryResponse(
        subjects=sorted(subjects),
        topics=sorted(topics),
        difficulties=["easy", "medium", "hard"],
    )


@app.get("/questions/search", response_model=list[QuestionResponse])
@app.get(
    "/api/v1/questions/search",
    response_model=list[QuestionResponse],
    include_in_schema=False,
)
def search_questions(
    subject: str | None = None,
    topic: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Question).where(Question.status == QuestionStatus.APPROVED)

    if subject:
        stmt = stmt.where(Question.subject == subject)
    if topic:
        stmt = stmt.where(Question.topic == topic)
    if category:
        stmt = stmt.where(or_(Question.subject == category, Question.topic == category))
    if difficulty:
        stmt = stmt.where(Question.difficulty == difficulty)
    stmt = stmt.order_by(Question.id.desc())
    return list(db.scalars(stmt).all())


@app.get("/questions/{question_id}", response_model=QuestionResponse)
@app.get(
    "/api/v1/questions/{question_id}",
    response_model=QuestionResponse,
    include_in_schema=False,
)
def read_question(
    question_id: int,
    db: Session = Depends(get_db),
):
    question = db.get(Question, question_id)
    if question is None or question.status != QuestionStatus.APPROVED:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@app.get("/questions", response_model=list[QuestionResponse])
@app.get(
    "/api/v1/questions",
    response_model=list[QuestionResponse],
    include_in_schema=False,
)
def list_questions(
    subject: str | None = None,
    topic: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
    creator_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(Question).where(Question.status == QuestionStatus.APPROVED)

    if subject:
        stmt = stmt.where(Question.subject == subject)
    if topic:
        stmt = stmt.where(Question.topic == topic)
    if category:
        stmt = stmt.where(or_(Question.subject == category, Question.topic == category))
    if difficulty:
        stmt = stmt.where(Question.difficulty == difficulty)
    if creator_id is not None:
        stmt = stmt.where(Question.creator_id == creator_id)
    stmt = stmt.order_by(Question.id.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


@app.patch("/questions/{question_id}", response_model=QuestionResponse)
@app.put(
    "/questions/{question_id}",
    response_model=QuestionResponse,
    include_in_schema=False,
)
@app.patch(
    "/api/v1/questions/{question_id}",
    response_model=QuestionResponse,
    include_in_schema=False,
)
def update_question(
    question_id: int,
    details: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a question. Authorized to the question creator or a moderator."""
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.creator_id != current_user.id and current_user.role != UserRole.MODERATOR:
        raise HTTPException(status_code=403, detail="You can only update your own questions")

    # Options and correct_answer_index validation
    new_options = details.options if details.options is not None else question.options
    new_correct_index = (
        details.correct_answer_index
        if details.correct_answer_index is not None
        else question.correct_answer_index
    )
    if new_correct_index >= len(new_options):
        raise HTTPException(
            status_code=422,
            detail="correct_answer_index must refer to an option",
        )

    # Content updates
    if details.question_text is not None:
        question.question_text = details.question_text
    if details.options is not None:
        question.options = details.options
    if details.correct_answer_index is not None:
        question.correct_answer_index = details.correct_answer_index
    if details.explanation is not None:
        question.explanation = details.explanation

    # Categorization updates (preserved if None in payload)
    if details.subject is not None:
        question.subject = details.subject
    if details.topic is not None:
        question.topic = details.topic
    if details.difficulty is not None:
        question.difficulty = details.difficulty

    # Creator edits to reviewed questions need moderator review again.
    if question.status != QuestionStatus.PENDING and current_user.role != UserRole.MODERATOR:
        question.status = QuestionStatus.PENDING
        question.moderator_id = None
        question.moderated_at = None
        question.moderation_comment = None

    db.commit()
    db.refresh(question)
    return question


@app.delete("/questions/{question_id}", response_model=MessageResponse)
@app.delete(
    "/api/v1/questions/{question_id}",
    response_model=MessageResponse,
    include_in_schema=False,
)
def delete_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a question. Authorized to the question creator or a moderator."""
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.creator_id != current_user.id and current_user.role != UserRole.MODERATOR:
        raise HTTPException(status_code=403, detail="You can only delete your own questions")

    db.delete(question)
    db.commit()
    return {"message": "Question deleted successfully"}


# --- Moderation Endpoints (Story #14) ---


@app.get("/moderation/questions", response_model=list[QuestionResponse])
@app.get(
    "/api/v1/moderation/questions",
    response_model=list[QuestionResponse],
    include_in_schema=False,
)
def review_submitted_questions(
    subject: str | None = None,
    topic: str | None = None,
    status_filter: QuestionStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """Allow authorized moderators to review submitted questions."""
    stmt = select(Question)
    if status_filter:
        stmt = stmt.where(Question.status == status_filter)
    if subject:
        stmt = stmt.where(Question.subject == subject)
    if topic:
        stmt = stmt.where(Question.topic == topic)
    stmt = stmt.order_by(Question.created_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


@app.patch("/questions/{question_id}/moderate", response_model=QuestionResponse)
@app.post(
    "/questions/{question_id}/moderate",
    response_model=QuestionResponse,
    include_in_schema=False,
)
@app.post(
    "/api/v1/questions/{question_id}/moderate",
    response_model=QuestionResponse,
    include_in_schema=False,
)
def moderate_question(
    question_id: int,
    decision: ModerateQuestionRequest,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """Approve or reject a question. Restricted to authorized moderators."""
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    target_status = (
        QuestionStatus.APPROVED
        if decision.status == "approved" or decision.action == "approve"
        else QuestionStatus.REJECTED
    )
    question.status = target_status
    question.moderator_id = moderator.id
    question.moderated_at = datetime.now(UTC)
    question.moderation_comment = decision.comment

    db.commit()
    db.refresh(question)
    return question


@app.post("/questions/{question_id}/approve", response_model=QuestionResponse)
@app.post(
    "/api/v1/questions/{question_id}/approve",
    response_model=QuestionResponse,
    include_in_schema=False,
)
def approve_question(
    question_id: int,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """Convenience endpoint: approve question."""
    return moderate_question(
        question_id=question_id,
        decision=ModerateQuestionRequest(status="approved"),
        moderator=moderator,
        db=db,
    )


@app.post("/questions/{question_id}/reject", response_model=QuestionResponse)
@app.post(
    "/api/v1/questions/{question_id}/reject",
    response_model=QuestionResponse,
    include_in_schema=False,
)
def reject_question(
    question_id: int,
    comment: str | None = None,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """Convenience endpoint: reject question."""
    return moderate_question(
        question_id=question_id,
        decision=ModerateQuestionRequest(status="rejected", comment=comment),
        moderator=moderator,
        db=db,
    )


@app.websocket("/ws/health")
async def websocket_health(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in frontend_origins:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text("pong" if message == "ping" else "Send ping")
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/quizzes/{quiz_id}")
async def quiz_updates(
    websocket: WebSocket,
    quiz_id: int,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """Stream a quiz's active question and answer/completion updates."""
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in frontend_origins:
        await websocket.close(code=1008)
        return

    secret = os.getenv("JWT_SECRET_KEY")
    if not token or not secret:
        await websocket.close(code=1008)
        return

    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
        token_version = int(payload["token_version"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        await websocket.close(code=1008)
        return

    user = db.get(User, user_id)
    quiz = load_quiz(db, quiz_id)
    if user is None or user.token_version != token_version or quiz is None:
        await websocket.close(code=1008)
        return

    has_active_attempt = db.scalar(
        select(QuizAttempt.id).where(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.student_id == user.id,
            QuizAttempt.status == AttemptStatus.ACTIVE,
        )
    ) is not None
    if quiz.host_id != user.id and not has_active_attempt:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    quiz_connections.setdefault(quiz_id, set()).add(websocket)
    await websocket.send_json({"event": "state", **public_quiz_response(quiz)})
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        quiz_connections.get(quiz_id, set()).discard(websocket)
        if not quiz_connections.get(quiz_id):
            quiz_connections.pop(quiz_id, None)
