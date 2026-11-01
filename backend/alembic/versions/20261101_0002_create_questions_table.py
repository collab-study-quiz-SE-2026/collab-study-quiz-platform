"""create questions table

Revision ID: 20261101_0002
Revises: 20261101_0001
"""

from alembic import op
import sqlalchemy as sa


revision = "20261101_0002"
down_revision = "20261101_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("correct_answer_index", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column(
            "difficulty",
            sa.String(length=20),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "creator_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_questions_topic", "questions", ["topic"], unique=False)
    op.create_index("ix_questions_creator_id", "questions", ["creator_id"], unique=False)


def downgrade():
    op.drop_index("ix_questions_creator_id", table_name="questions")
    op.drop_index("ix_questions_topic", table_name="questions")
    op.drop_table("questions")
