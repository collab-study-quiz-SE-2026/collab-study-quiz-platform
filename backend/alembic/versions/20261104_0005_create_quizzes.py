"""create quizzes and quiz question selections

Revision ID: 20261104_0005
Revises: 20261101_0004
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0005"
down_revision = "20261101_0004"
branch_labels = None
depends_on = None


def upgrade():
    quiz_status = postgresql.ENUM(
        "DRAFT", "PUBLISHED", "LIVE", "COMPLETED",
        name="quiz_status", create_type=False,
    )
    quiz_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "quizzes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("room_code", sa.String(length=6), nullable=False),
        sa.Column("status", quiz_status, nullable=False, server_default="PUBLISHED"),
        sa.Column("host_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("room_code"),
    )
    op.create_index("ix_quizzes_host_id", "quizzes", ["host_id"])
    op.create_index("ix_quizzes_room_code", "quizzes", ["room_code"])
    op.create_index("ix_quizzes_status", "quizzes", ["status"])
    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("quiz_id", "question_id"),
        sa.UniqueConstraint("quiz_id", "position"),
    )
    op.create_index("ix_quiz_questions_question_id", "quiz_questions", ["question_id"])


def downgrade():
    op.drop_index("ix_quiz_questions_question_id", table_name="quiz_questions")
    op.drop_table("quiz_questions")
    op.drop_index("ix_quizzes_status", table_name="quizzes")
    op.drop_index("ix_quizzes_room_code", table_name="quizzes")
    op.drop_index("ix_quizzes_host_id", table_name="quizzes")
    op.drop_table("quizzes")
    sa.Enum(name="quiz_status").drop(op.get_bind(), checkfirst=True)
