"""track the active question in a quiz room

Revision ID: 20261107_0007
Revises: 20261104_0006
"""

from alembic import op
import sqlalchemy as sa


revision = "20261107_0007"
down_revision = "20261104_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "quizzes",
        sa.Column("active_question_position", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column("quizzes", "active_question_position")
