"""add database-backed multi-user authentication

Revision ID: 0006_multi_user_auth
Revises: 0005_generic_workflows
Create Date: 2026-08-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_multi_user_auth"
down_revision: Union[str, None] = "0005_generic_workflows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))
    op.create_index("uq_users_username", "users", ["username"], unique=True)
    op.execute(
        """
        update users
        set username = 'admin'
        where id = '00000000-0000-0000-0000-000000000001'
          and username is null
        """
    )


def downgrade() -> None:
    op.drop_index("uq_users_username", table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
