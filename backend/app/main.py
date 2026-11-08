from datetime import UTC, datetime
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
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import Question, QuestionStatus, StudyMaterial, User, UserRole
from app.schemas import (
    CategorySummaryResponse,
    LoginRequest,
    MessageResponse,
    ModerateQuestionRequest,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    RegistrationRequest,
    RegistrationResponse,
    TokenResponse,
    UserResponse,
    StudyMaterialResponse,
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
    subject: str | None = None,
    topic: str | None = None,
    tag: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List study materials, optionally filtered by subject, topic, or tag."""
    stmt = select(StudyMaterial)

    if subject:
        stmt = stmt.where(StudyMaterial.subject == subject.strip())

    if topic:
        stmt = stmt.where(StudyMaterial.topic == topic.strip())

    materials = list(
        db.scalars(stmt.order_by(StudyMaterial.created_at.desc())).all()
    )

    # Tags are stored as a JSON list. Filter them in Python for exact,
    # case-insensitive matching across supported database engines.
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