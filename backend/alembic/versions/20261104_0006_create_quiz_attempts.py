"""create quiz attempts

Revision ID: 20261104_0006
Revises: 20261104_0005
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0006"
down_revision = "20261104_0005"
branch_labels = None
depends_on = None


def upgrade():
    attempt_status = postgresql.ENUM(
        "ACTIVE", "COMPLETED", "EXPIRED", name="attempt_status", create_type=False
    )
    attempt_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", attempt_status, nullable=False, server_default="ACTIVE"),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("question_timings", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_quiz_attempts_quiz_id", "quiz_attempts", ["quiz_id"])
    op.create_index("ix_quiz_attempts_student_id", "quiz_attempts", ["student_id"])
    op.create_index("ix_quiz_attempts_status", "quiz_attempts", ["status"])


def downgrade():
    op.drop_index("ix_quiz_attempts_status", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_student_id", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_quiz_id", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
    sa.Enum(name="attempt_status").drop(op.get_bind(), checkfirst=True)
