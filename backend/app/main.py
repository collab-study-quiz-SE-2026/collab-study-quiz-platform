from datetime import UTC, datetime
import os
from contextlib import closing

import psycopg
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import Question, QuestionStatus, User, UserRole
from app.schemas import (
    LoginRequest,
    MessageResponse,
    ModerateQuestionRequest,
    QuestionCreate,
    QuestionResponse,
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
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


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


@app.get("/questions/search", response_model=list[QuestionResponse])
@app.get(
    "/api/v1/questions/search",
    response_model=list[QuestionResponse],
    include_in_schema=False,
)
def search_questions(
    topic: str | None = None,
    difficulty: str | None = None,
    status_filter: QuestionStatus | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Question)
    if status_filter:
        stmt = stmt.where(Question.status == status_filter)
    else:
        # Exclude rejected questions from published search results
        stmt = stmt.where(Question.status != QuestionStatus.REJECTED)

    if topic:
        stmt = stmt.where(Question.topic == topic)
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
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@app.get("/questions", response_model=list[QuestionResponse])
@app.get(
    "/api/v1/questions",
    response_model=list[QuestionResponse],
    include_in_schema=False,
)
def list_questions(
    topic: str | None = None,
    difficulty: str | None = None,
    creator_id: int | None = None,
    status_filter: QuestionStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(Question)
    if status_filter:
        stmt = stmt.where(Question.status == status_filter)
    else:
        # Exclude rejected questions from published sets
        stmt = stmt.where(Question.status != QuestionStatus.REJECTED)

    if topic:
        stmt = stmt.where(Question.topic == topic)
    if difficulty:
        stmt = stmt.where(Question.difficulty == difficulty)
    if creator_id is not None:
        stmt = stmt.where(Question.creator_id == creator_id)
    stmt = stmt.order_by(Question.id.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


# --- Moderation Endpoints (Story #14) ---


@app.get("/moderation/questions", response_model=list[QuestionResponse])
@app.get(
    "/api/v1/moderation/questions",
    response_model=list[QuestionResponse],
    include_in_schema=False,
)
def review_submitted_questions(
    status_filter: QuestionStatus | None = None,
    topic: str | None = None,
    limit: int = 50,
    offset: int = 0,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """Allow authorized moderators to review submitted questions."""
    stmt = select(Question)
    if status_filter:
        stmt = stmt.where(Question.status == status_filter)
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
