"""add question moderation columns

Revision ID: 20261101_0003
Revises: 20261101_0002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261101_0003"
down_revision = "20261101_0002"
branch_labels = None
depends_on = None


def upgrade():
    question_status = postgresql.ENUM(
        "PENDING", "APPROVED", "REJECTED", name="question_status", create_type=False
    )
    question_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "questions",
        sa.Column(
            "status",
            question_status,
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.add_column(
        "questions",
        sa.Column(
            "moderator_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "questions",
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("moderation_comment", sa.Text(), nullable=True),
    )
    op.create_index("ix_questions_status", "questions", ["status"], unique=False)


def downgrade():
    op.drop_index("ix_questions_status", table_name="questions")
    op.drop_column("questions", "moderation_comment")
    op.drop_column("questions", "moderated_at")
    op.drop_column("questions", "moderator_id")
    op.drop_column("questions", "status")
    sa.Enum(name="question_status").drop(op.get_bind(), checkfirst=True)
