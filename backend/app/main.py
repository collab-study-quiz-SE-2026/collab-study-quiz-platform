from datetime import UTC, datetime, timedelta
import os
from contextlib import closing
from pathlib import Path
from uuid import uuid4
from urllib.parse import quote

import psycopg
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import (
    AttemptStatus,
    Question,
    QuestionStatus,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    QuizStatus,
    StudyMaterial,
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
    QuizCreate,
    QuizAttemptResponse,
    QuizAttemptHistoryResponse,
    QuizResponse,
    RegistrationRequest,
    RegistrationResponse,
    TokenResponse,
    UserResponse,
    StudyMaterialResponse,
    LearningProgressPoint,
    TopicProgressPoint,
    TopicProgressTrend,
    LearningProgressResponse,
    TopicPerformanceDetail,
    TopicPerformanceResponse,
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
    evaluated = (
        attempt.status in (AttemptStatus.COMPLETED, AttemptStatus.EXPIRED)
        and attempt.correct_answer_count is not None
    )
    total_questions = len(attempt.quiz.questions)
    correct_answers = attempt.correct_answer_count if evaluated else None
    return {
        "id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "student_id": attempt.student_id,
        "status": attempt.status,
        "score": attempt.score,
        "accuracy": attempt.score if evaluated else None,
        "correct_answers": correct_answers,
        "incorrect_answers": (
            total_questions - correct_answers if evaluated else None
        ),
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


def evaluate_attempt(attempt: QuizAttempt) -> int:
    """Count correct submitted answers; unanswered questions count as incorrect."""
    return sum(
        int(
            str(link.question.id) in attempt.answers
            and attempt.answers[str(link.question.id)]
            == link.question.correct_answer_index
        )
        for link in attempt.quiz.questions
    )


def save_attempt_result(attempt: QuizAttempt, now: datetime, expired: bool) -> None:
    total_questions = len(attempt.quiz.questions)
    correct_answers = evaluate_attempt(attempt)
    attempt.correct_answer_count = correct_answers
    attempt.score = round(correct_answers * 100 / total_questions) if total_questions else 0
    attempt.status = AttemptStatus.EXPIRED if expired else AttemptStatus.COMPLETED
    attempt.completed_at = now


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
    )
    quiz.questions = [
        QuizQuestion(question=questions_by_id[question_id], position=position)
        for position, question_id in enumerate(details.question_ids)
    ]
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz_response(quiz)


@app.get("/quizzes/{quiz_id}", response_model=QuizResponse)
@app.get(
    "/api/v1/quizzes/{quiz_id}",
    response_model=QuizResponse,
    include_in_schema=False,
)
def read_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.scalar(
        select(Quiz)
        .options(selectinload(Quiz.questions).selectinload(QuizQuestion.question))
        .where(Quiz.id == quiz_id)
    )
    if quiz is None or quiz.status == QuizStatus.DRAFT:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz_response(quiz)


@app.get("/quizzes", response_model=list[QuizResponse])
@app.get("/api/v1/quizzes", response_model=list[QuizResponse], include_in_schema=False)
def list_quizzes(db: Session = Depends(get_db)):
    quizzes = db.scalars(
        select(Quiz)
        .options(selectinload(Quiz.questions).selectinload(QuizQuestion.question))
        .where(Quiz.status.in_([QuizStatus.PUBLISHED, QuizStatus.LIVE]))
        .order_by(Quiz.created_at.desc(), Quiz.id.desc())
    ).all()
    return [quiz_response(quiz) for quiz in quizzes]


def start_attempt(
    quiz: Quiz,
    current_user: User,
    db: Session,
) -> dict:
    now = datetime.now(UTC)
    if quiz.status not in (QuizStatus.PUBLISHED, QuizStatus.LIVE):
        raise HTTPException(status_code=409, detail="Quiz is not available")
    existing = active_attempt(db, quiz.id, current_user.id)
    if existing is not None:
        return attempt_response(existing)
    count = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz.id,
        QuizAttempt.student_id == current_user.id,
        QuizAttempt.status.in_([AttemptStatus.COMPLETED, AttemptStatus.EXPIRED]),
    ).count()
    if count >= quiz.max_attempts:
        raise HTTPException(status_code=409, detail="Maximum quiz attempts reached")
    attempt = QuizAttempt(quiz=quiz, student=current_user, started_at=now)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt_response(attempt)


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
def submit_answer(
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
        save_attempt_result(attempt, now, expired=True)
        db.commit()
        raise HTTPException(status_code=409, detail="Quiz time limit has expired")
    selected = next(
        (link.question for link in attempt.quiz.questions if link.question.id == answer.question_id),
        None,
    )
    if selected is None:
        raise HTTPException(status_code=422, detail="Question is not part of this quiz")
    if answer.answer_index >= len(selected.options):
        raise HTTPException(status_code=422, detail="Answer index is invalid")
    attempt.answers = {**attempt.answers, str(answer.question_id): answer.answer_index}
    attempt.question_timings = {
        **attempt.question_timings,
        str(answer.question_id): answer.time_spent_seconds,
    }
    db.commit()
    db.refresh(attempt)
    return attempt_response(attempt)


@app.post("/quiz-sessions/{attempt_id}/complete", response_model=QuizAttemptResponse)
@app.post(
    "/api/v1/quiz-sessions/{attempt_id}/complete",
    response_model=QuizAttemptResponse,
    include_in_schema=False,
)
def complete_quiz(
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
    save_attempt_result(attempt, now, expired=attempt_expired(attempt, now))
    db.commit()
    db.refresh(attempt)
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


def build_topic_performance(
    student_id: int,
    db: Session,
    subject: str | None = None,
) -> dict:
    attempts = db.scalars(
        select(QuizAttempt)
        .options(
            selectinload(QuizAttempt.quiz)
            .selectinload(Quiz.questions)
            .selectinload(QuizQuestion.question)
        )
        .where(
            QuizAttempt.student_id == student_id,
            QuizAttempt.status == AttemptStatus.COMPLETED,
        )
        .order_by(QuizAttempt.completed_at.asc(), QuizAttempt.id.asc())
    ).all()

    student_topic_data: dict[tuple[str, str], dict] = {}
    total_questions_evaluated = 0

    for attempt in attempts:
        question_by_id = {
            str(link.question.id): link.question for link in attempt.quiz.questions
        }
        for q_id_str, answer_index in attempt.answers.items():
            question = question_by_id.get(str(q_id_str))
            if question is None:
                continue

            q_subject = question.subject or "General"
            q_topic = question.topic

            if subject and q_subject.lower() != subject.strip().lower():
                continue

            key = (q_subject, q_topic)
            if key not in student_topic_data:
                student_topic_data[key] = {
                    "total_questions": 0,
                    "correct_answers": 0,
                    "timings": [],
                }

            student_topic_data[key]["total_questions"] += 1
            total_questions_evaluated += 1
            if answer_index == question.correct_answer_index:
                student_topic_data[key]["correct_answers"] += 1

            timing = attempt.question_timings.get(str(q_id_str))
            if timing is None and str(q_id_str).isdigit():
                timing = attempt.question_timings.get(int(q_id_str))
            if timing is not None and isinstance(timing, (int, float)):
                student_topic_data[key]["timings"].append(timing)

    # Cohort analysis across all completed attempts for relevant topics
    all_completed_attempts = db.scalars(
        select(QuizAttempt)
        .options(
            selectinload(QuizAttempt.quiz)
            .selectinload(Quiz.questions)
            .selectinload(QuizQuestion.question)
        )
        .where(
            QuizAttempt.status == AttemptStatus.COMPLETED,
        )
    ).all()

    cohort_by_topic: dict[str, dict[int, list[int]]] = {}
    for a in all_completed_attempts:
        q_map = {str(link.question.id): link.question for link in a.quiz.questions}
        for q_id_str, ans_idx in a.answers.items():
            q = q_map.get(str(q_id_str))
            if q is None:
                continue
            t_name = q.topic
            if t_name not in cohort_by_topic:
                cohort_by_topic[t_name] = {}
            if a.student_id not in cohort_by_topic[t_name]:
                cohort_by_topic[t_name][a.student_id] = [0, 0]
            cohort_by_topic[t_name][a.student_id][1] += 1
            if ans_idx == q.correct_answer_index:
                cohort_by_topic[t_name][a.student_id][0] += 1

    topics_list = []
    strong_topics = []
    weak_topics = []

    for (q_subject, q_topic), data in sorted(
        student_topic_data.items(), key=lambda item: (item[0][0], item[0][1])
    ):
        total_q = data["total_questions"]
        correct_q = data["correct_answers"]
        accuracy = round(100.0 * correct_q / total_q, 2) if total_q > 0 else 0.0

        avg_time = (
            round(sum(data["timings"]) / len(data["timings"]), 2)
            if data["timings"]
            else None
        )

        if accuracy >= 75.0:
            strength = "strong"
            strong_topics.append(q_topic)
        elif accuracy >= 50.0:
            strength = "moderate"
        else:
            strength = "weak"
            weak_topics.append(q_topic)

        cohort_students = cohort_by_topic.get(q_topic, {})
        cohort_percentile = None
        if cohort_students:
            cohort_accuracies = [
                (stats[0] / stats[1] * 100.0)
                for stats in cohort_students.values()
                if stats[1] > 0
            ]
            if cohort_accuracies:
                cohort_percentile = round(
                    100.0 * sum(c_acc <= accuracy for c_acc in cohort_accuracies)
                    / len(cohort_accuracies),
                    2,
                )

        topics_list.append(
            {
                "subject": q_subject,
                "topic": q_topic,
                "total_questions": total_q,
                "correct_answers": correct_q,
                "accuracy_percentage": accuracy,
                "average_time_seconds": avg_time,
                "cohort_percentile": cohort_percentile,
                "strength_level": strength,
            }
        )

    return {
        "student_id": student_id,
        "total_quizzes_evaluated": len(attempts),
        "total_questions_evaluated": total_questions_evaluated,
        "topics": topics_list,
        "strong_topics": list(dict.fromkeys(strong_topics)),
        "weak_topics": list(dict.fromkeys(weak_topics)),
    }


@app.get("/analytics/topics", response_model=TopicPerformanceResponse)
@app.get("/analytics/topics/me", response_model=TopicPerformanceResponse)
@app.get(
    "/api/v1/analytics/topics",
    response_model=TopicPerformanceResponse,
    include_in_schema=False,
)
@app.get(
    "/api/v1/analytics/topics/me",
    response_model=TopicPerformanceResponse,
    include_in_schema=False,
)
def read_my_topic_performance(
    subject: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_topic_performance(current_user.id, db, subject=subject)


@app.get(
    "/users/{student_id}/analytics/topics",
    response_model=TopicPerformanceResponse,
)
@app.get(
    "/api/v1/users/{student_id}/analytics/topics",
    response_model=TopicPerformanceResponse,
    include_in_schema=False,
)
def read_student_topic_performance(
    student_id: int,
    subject: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id != student_id and current_user.role != UserRole.MODERATOR:
        raise HTTPException(
            status_code=403,
            detail="You can only access your own topic performance analytics",
        )
    if db.get(User, student_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    return build_topic_performance(student_id, db, subject=subject)


def build_learning_progress(student_id: int, db: Session) -> dict:
    attempts = db.scalars(
        select(QuizAttempt)
        .options(
            selectinload(QuizAttempt.quiz)
            .selectinload(Quiz.questions)
            .selectinload(QuizQuestion.question)
        )
        .where(
            QuizAttempt.student_id == student_id,
            QuizAttempt.status == AttemptStatus.COMPLETED,
        )
        .order_by(QuizAttempt.completed_at.asc(), QuizAttempt.id.asc())
    ).all()

    if not attempts:
        return {
            "student_id": student_id,
            "total_quizzes_completed": 0,
            "average_score": None,
            "highest_score": None,
            "lowest_score": None,
            "initial_score": None,
            "latest_score": None,
            "overall_improvement": None,
            "trend_direction": "insufficient_data",
            "timeline": [],
            "topic_trends": [],
        }

    scores = [attempt.score for attempt in attempts if attempt.score is not None]
    average_score = round(sum(scores) / len(scores), 2) if scores else None
    highest_score = max(scores) if scores else None
    lowest_score = min(scores) if scores else None
    initial_score = scores[0] if scores else None
    latest_score = scores[-1] if scores else None
    overall_improvement = (
        round(float(latest_score - initial_score), 2)
        if latest_score is not None and initial_score is not None
        else None
    )

    if len(scores) < 2:
        trend_direction = "stable"
    elif latest_score > initial_score:
        trend_direction = "improving"
    elif latest_score < initial_score:
        trend_direction = "declining"
    else:
        trend_direction = "stable"

    timeline = []
    running_scores: list[int] = []
    topic_history_map: dict[tuple[str, str], list[dict]] = {}

    for attempt in attempts:
        score = attempt.score or 0
        running_scores.append(score)
        moving_avg = round(sum(running_scores) / len(running_scores), 2)

        if len(running_scores) == 1:
            trajectory = "stable"
        elif score > running_scores[-2]:
            trajectory = "improving"
        elif score < running_scores[-2]:
            trajectory = "declining"
        else:
            trajectory = "stable"

        duration_seconds = None
        if attempt.started_at and attempt.completed_at:
            duration_seconds = int(
                (attempt.completed_at - attempt.started_at).total_seconds()
            )

        total_questions = len(attempt.quiz.questions)
        correct_count = (
            attempt.correct_answer_count
            if attempt.correct_answer_count is not None
            else 0
        )
        accuracy = (
            round(100.0 * correct_count / total_questions, 2)
            if total_questions > 0
            else 0.0
        )

        timeline.append(
            {
                "attempt_id": attempt.id,
                "quiz_id": attempt.quiz_id,
                "quiz_title": attempt.quiz.title,
                "completed_at": attempt.completed_at,
                "score": score,
                "accuracy_percentage": accuracy,
                "correct_answers": correct_count,
                "total_questions": total_questions,
                "duration_seconds": duration_seconds,
                "moving_average_score": moving_avg,
                "trajectory": trajectory,
            }
        )

        attempt_q_map = {
            str(link.question.id): link.question for link in attempt.quiz.questions
        }
        attempt_topic_stats: dict[tuple[str, str], list[int]] = {}
        for q_id_str, ans_idx in attempt.answers.items():
            q = attempt_q_map.get(str(q_id_str))
            if q is None:
                continue
            key = (q.subject or "General", q.topic)
            if key not in attempt_topic_stats:
                attempt_topic_stats[key] = [0, 0]
            attempt_topic_stats[key][1] += 1
            if ans_idx == q.correct_answer_index:
                attempt_topic_stats[key][0] += 1

        for key, counts in attempt_topic_stats.items():
            if key not in topic_history_map:
                topic_history_map[key] = []
            topic_acc = (
                round(100.0 * counts[0] / counts[1], 2) if counts[1] > 0 else 0.0
            )
            topic_history_map[key].append(
                {
                    "completed_at": attempt.completed_at,
                    "quiz_id": attempt.quiz_id,
                    "quiz_title": attempt.quiz.title,
                    "correct_answers": counts[0],
                    "total_questions": counts[1],
                    "accuracy_percentage": topic_acc,
                }
            )

    topic_trends = []
    for (subj, top), hist in sorted(topic_history_map.items()):
        total_correct = sum(p["correct_answers"] for p in hist)
        total_q = sum(p["total_questions"] for p in hist)
        curr_acc = round(100.0 * total_correct / total_q, 2) if total_q > 0 else 0.0
        topic_trends.append(
            {
                "subject": subj,
                "topic": top,
                "total_attempts": len(hist),
                "current_accuracy": curr_acc,
                "history": hist,
            }
        )

    return {
        "student_id": student_id,
        "total_quizzes_completed": len(attempts),
        "average_score": average_score,
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "initial_score": initial_score,
        "latest_score": latest_score,
        "overall_improvement": overall_improvement,
        "trend_direction": trend_direction,
        "timeline": timeline,
        "topic_trends": topic_trends,
    }


@app.get("/analytics/progress", response_model=LearningProgressResponse)
@app.get("/analytics/progress/me", response_model=LearningProgressResponse)
@app.get(
    "/api/v1/analytics/progress",
    response_model=LearningProgressResponse,
    include_in_schema=False,
)
@app.get(
    "/api/v1/analytics/progress/me",
    response_model=LearningProgressResponse,
    include_in_schema=False,
)
def read_my_learning_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_learning_progress(current_user.id, db)


@app.get(
    "/users/{student_id}/analytics/progress",
    response_model=LearningProgressResponse,
)
@app.get(
    "/api/v1/users/{student_id}/analytics/progress",
    response_model=LearningProgressResponse,
    include_in_schema=False,
)
def read_student_learning_progress(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id != student_id and current_user.role != UserRole.MODERATOR:
        raise HTTPException(
            status_code=403,
            detail="You can only access your own learning progress analytics",
        )
    if db.get(User, student_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    return build_learning_progress(student_id, db)


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


MAX_UPLOAD_SIZE = 25 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf": ("pdf", "application/pdf"),
    ".md": ("markdown", "text/markdown"),
    ".markdown": ("markdown", "text/markdown"),
}


@app.post(
    "/materials/upload",
    response_model=StudyMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_study_material(
    title: str = Form(..., min_length=1, max_length=200),
    course_code: str = Form(..., min_length=1, max_length=50),
    subject: str = Form(default="General", min_length=1, max_length=100),
    topic: str = Form(default="General", min_length=1, max_length=100),
    tags: str = Form(default=""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = title.strip()
    course_code = course_code.strip()
    subject = subject.strip()
    topic = topic.strip()

    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be blank")

    if not course_code:
        raise HTTPException(status_code=422, detail="Course code cannot be blank")

    if not subject:
        raise HTTPException(status_code=422, detail="Subject cannot be blank")

    if not topic:
        raise HTTPException(status_code=422, detail="Topic cannot be blank")

    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and Markdown files are allowed",
        )

    file_type, mime_type = ALLOWED_EXTENSIONS[extension]

    if file.content_type not in (mime_type, "application/octet-stream"):
        raise HTTPException(
            status_code=400,
            detail="File content type does not match the file extension",
        )

    tag_list = list(dict.fromkeys(
        tag.strip() for tag in tags.split(",") if tag.strip()
    ))

    storage_key = f"study-materials/{uuid4()}{extension}"
    payload = bytearray()

    try:
        while True:
            chunk = file.file.read(1024 * 1024)

            if not chunk:
                break

            payload.extend(chunk)

            if len(payload) > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="File size exceeds the 25 MB limit",
                )

        if not payload:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file cannot be empty",
            )

        if extension == ".pdf" and not payload.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file content",
            )

        if extension in (".md", ".markdown"):
            try:
                payload.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Markdown file must contain valid UTF-8 text",
                ) from None

        with closing(get_storage_client()) as storage:
            storage.put_object(
                Bucket=os.environ["S3_BUCKET"],
                Key=storage_key,
                Body=bytes(payload),
                ContentType=mime_type,
            )

        material = StudyMaterial(
            title=title,
            course_code=course_code,
            subject=subject,
            topic=topic,
            tags=tag_list,
            original_filename=file.filename or "uploaded-file",
            storage_key=storage_key,
            file_type=file_type,
            mime_type=mime_type,
            file_size=len(payload),
            uploader_id=current_user.id,
        )

        db.add(material)
        db.commit()
        db.refresh(material)

        return material

    except HTTPException:
        raise

    except Exception:
        db.rollback()

        try:
            with closing(get_storage_client()) as storage:
                storage.delete_object(
                    Bucket=os.environ["S3_BUCKET"],
                    Key=storage_key,
                )
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail="Unable to upload study material",
        ) from None

    finally:
        file.file.close()


@app.get("/materials", response_model=list[StudyMaterialResponse])
def list_study_materials(
    search: str | None = None,
    subject: str | None = None,
    topic: str | None = None,
    tag: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List study materials with optional search and category filters."""
    stmt = select(StudyMaterial)

    if subject and subject.strip():
        stmt = stmt.where(StudyMaterial.subject == subject.strip())

    if topic and topic.strip():
        stmt = stmt.where(StudyMaterial.topic == topic.strip())

    # Prepare the search term. Search is applied after fetching
    # records so tags are included along with title and course code.
    search_term = search.strip() if search else ""

    materials = list(
        db.scalars(stmt.order_by(StudyMaterial.created_at.desc())).all()
    )

    # Filter tags using case-insensitive exact matching.
    if tag and tag.strip():
        requested_tag = tag.strip().casefold()
        materials = [
            material
            for material in materials
            if any(
                isinstance(existing_tag, str)
                and existing_tag.casefold() == requested_tag
                for existing_tag in (material.tags or [])
            )
        ]

    # Also include materials whose tags contain the search term.
    if search_term:
        requested_search = search_term.casefold()
        materials = [
            material
            for material in materials
            if (
                requested_search in material.title.casefold()
                or requested_search in (material.course_code or "").casefold()
                or any(
                    isinstance(existing_tag, str)
                    and requested_search in existing_tag.casefold()
                    for existing_tag in (material.tags or [])
                )
            )
        ]

    return materials

@app.get("/materials/{material_id}/download")
def download_study_material(
    material_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    material = db.get(StudyMaterial, material_id)

    if material is None:
        raise HTTPException(
            status_code=404,
            detail="Study material not found",
        )

    try:
        with closing(get_storage_client()) as storage:
            stored_object = storage.get_object(
                Bucket=os.environ["S3_BUCKET"],
                Key=material.storage_key,
            )
            file_content = stored_object["Body"].read()
            stored_object["Body"].close()

    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")

        if error_code in ("NoSuchKey", "404", "NotFound"):
            raise HTTPException(
                status_code=404,
                detail="Study material file not found in storage",
            ) from None

        raise HTTPException(
            status_code=503,
            detail="Storage service is unavailable",
        ) from None

    except BotoCoreError:
        raise HTTPException(
            status_code=503,
            detail="Storage service is unavailable",
        ) from None

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve study material",
        ) from None

    filename = quote(Path(material.original_filename).name)

    return Response(
        content=file_content,
        media_type=material.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Content-Length": str(len(file_content)),
            "X-Content-Type-Options": "nosniff",
        },
    )
