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

    questions: Mapped[list["Question"]] = relationship("Question", back_populates="creator")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_topic", "topic"),
        Index("ix_questions_creator_id", "creator_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_text: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON)
    correct_answer_index: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(String(100))
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    creator: Mapped["User"] = relationship("User", back_populates="questions")
