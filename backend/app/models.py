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


class QuizStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    LIVE = "live"
    COMPLETED = "completed"


class AttemptStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


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
    quizzes: Mapped[list["Quiz"]] = relationship(
        "Quiz",
        foreign_keys="Quiz.host_id",
        back_populates="host",
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


class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = (
        UniqueConstraint("room_code"),
        Index("ix_quizzes_host_id", "host_id"),
        Index("ix_quizzes_room_code", "room_code"),
        Index("ix_quizzes_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    room_code: Mapped[str] = mapped_column(String(6), unique=True)
    status: Mapped[QuizStatus] = mapped_column(
        SqlEnum(QuizStatus, name="quiz_status"), default=QuizStatus.PUBLISHED
    )
    host_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active_question_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    host: Mapped["User"] = relationship(
        "User", foreign_keys=[host_id], back_populates="quizzes"
    )
    questions: Mapped[list["QuizQuestion"]] = relationship(
        "QuizQuestion", back_populates="quiz", cascade="all, delete-orphan",
        order_by="QuizQuestion.position",
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint("quiz_id", "question_id"),
        UniqueConstraint("quiz_id", "position"),
        Index("ix_quiz_questions_question_id", "question_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"))
    position: Mapped[int] = mapped_column(Integer)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")
    question: Mapped["Question"] = relationship("Question")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        Index("ix_quiz_attempts_quiz_id", "quiz_id"),
        Index("ix_quiz_attempts_student_id", "student_id"),
        Index("ix_quiz_attempts_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[AttemptStatus] = mapped_column(
        SqlEnum(AttemptStatus, name="attempt_status"), default=AttemptStatus.ACTIVE
    )
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    question_timings: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    quiz: Mapped["Quiz"] = relationship("Quiz")
    student: Mapped["User"] = relationship("User")
