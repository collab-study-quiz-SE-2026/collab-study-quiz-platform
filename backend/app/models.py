from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, Enum):
    STUDENT = "student"
    MODERATOR = "moderator"


class QuestionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email"),
        Index("ix_users_email", "email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    password_hash: Mapped[str] = mapped_column(String(60))
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role"), default=UserRole.STUDENT
    )
    token_version: Mapped[int] = mapped_column(default=0)

    questions: Mapped[list["Question"]] = relationship(
        "Question",
        foreign_keys="Question.creator_id",
        back_populates="creator",
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_subject", "subject"),
        Index("ix_questions_topic", "topic"),
        Index("ix_questions_difficulty", "difficulty"),
        Index("ix_questions_creator_id", "creator_id"),
        Index("ix_questions_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_text: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON)
    correct_answer_index: Mapped[int] = mapped_column(Integer)
    subject: Mapped[str] = mapped_column(String(100), default="General")
    topic: Mapped[str] = mapped_column(String(100))
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[QuestionStatus] = mapped_column(
        SqlEnum(QuestionStatus, name="question_status"),
        default=QuestionStatus.PENDING,
    )
    moderator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    moderated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    moderation_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[creator_id],
        back_populates="questions",
    )
    moderator: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[moderator_id],
    )


class StudyMaterial(Base):
    __tablename__ = "study_materials"
    __table_args__ = (
        Index("ix_study_materials_course_code", "course_code"),
        Index("ix_study_materials_uploader_id", "uploader_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    course_code: Mapped[str] = mapped_column(String(50))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    file_type: Mapped[str] = mapped_column(String(20))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)

    uploader_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
