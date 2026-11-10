"""remove the unused legacy materials table

Revision ID: 20261110_0006
Revises: 20261109_0005
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261110_0006"
down_revision = "20261109_0005"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("materials"):
        return

    row_count = bind.execute(sa.text("SELECT count(*) FROM materials")).scalar_one()
    if row_count:
        raise RuntimeError(
            "The legacy materials table contains data. Move or back up those rows "
            "before applying this migration; it will not delete them."
        )

    op.drop_table("materials")
    postgresql.ENUM(name="material_status").drop(bind, checkfirst=True)


def downgrade():
    bind = op.get_bind()
    material_status = postgresql.ENUM(
        "PUBLISHED", "HIDDEN", name="material_status", create_type=False
    )
    material_status.create(bind, checkfirst=True)
    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("course_code", sa.String(length=50), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False, unique=True),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            material_status,
            nullable=False,
            server_default="PUBLISHED",
        ),
        sa.Column(
            "uploader_id",
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
    op.create_index("ix_materials_status", "materials", ["status"])
    op.create_index("ix_materials_course_code", "materials", ["course_code"])
    op.create_index("ix_materials_uploader_id", "materials", ["uploader_id"])
