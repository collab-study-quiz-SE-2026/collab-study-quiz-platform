"""create users table

Revision ID: 20261101_0001
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261101_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    user_role = postgresql.ENUM(
        "STUDENT", "MODERATOR", name="user_role", create_type=False
    )
    user_role.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=60), nullable=False),
        sa.Column(
            "role",
            user_role,
            nullable=False,
            server_default="STUDENT",
        ),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)


def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
