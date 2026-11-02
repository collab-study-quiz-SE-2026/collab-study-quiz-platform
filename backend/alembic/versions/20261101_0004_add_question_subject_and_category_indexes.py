"""add question subject and category indexes

Revision ID: 20261101_0004
Revises: 20261101_0003
"""

from alembic import op
import sqlalchemy as sa


revision = "20261101_0004"
down_revision = "20261101_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "questions",
        sa.Column(
            "subject",
            sa.String(length=100),
            nullable=False,
            server_default="General",
        ),
    )
    op.create_index("ix_questions_subject", "questions", ["subject"], unique=False)
    op.create_index("ix_questions_difficulty", "questions", ["difficulty"], unique=False)


def downgrade():
    op.drop_index("ix_questions_difficulty", table_name="questions")
    op.drop_index("ix_questions_subject", table_name="questions")
    op.drop_column("questions", "subject")
