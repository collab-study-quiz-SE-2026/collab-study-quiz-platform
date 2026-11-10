"""add study material subject and topic

Revision ID: beedc533b405
Revises: c53375cc9a34
"""

from alembic import op
import sqlalchemy as sa


revision = "beedc533b405"
down_revision = "c53375cc9a34"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "study_materials",
        sa.Column(
            "subject",
            sa.String(length=100),
            nullable=False,
            server_default="General",
        ),
    )

    op.add_column(
        "study_materials",
        sa.Column(
            "topic",
            sa.String(length=100),
            nullable=False,
            server_default="General",
        ),
    )

    op.create_index(
        "ix_study_materials_subject",
        "study_materials",
        ["subject"],
        unique=False,
    )

    op.create_index(
        "ix_study_materials_topic",
        "study_materials",
        ["topic"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_study_materials_topic", table_name="study_materials")
    op.drop_index("ix_study_materials_subject", table_name="study_materials")

    op.drop_column("study_materials", "topic")
    op.drop_column("study_materials", "subject")