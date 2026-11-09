"""store the number of correct answers for completed quiz attempts

Revision ID: 20261108_0008
Revises: 20261108_0007
"""

from alembic import op
import sqlalchemy as sa


revision = "20261108_0008"
down_revision = "20261108_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "quiz_attempts",
        sa.Column("correct_answer_count", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column("quiz_attempts", "correct_answer_count")
