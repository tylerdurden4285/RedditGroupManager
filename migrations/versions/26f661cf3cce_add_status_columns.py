from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = '26f661cf3cce'
down_revision: Union[str, None] = '2efa0e31c863'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status-related columns to posts table if missing."""
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
    ).fetchone()
    if not exists:
        return
    res = conn.execute(sa.text("PRAGMA table_info(posts)")).fetchall()
    columns = [r[1] for r in res]
    if "status" not in columns:
        op.add_column("posts", sa.Column("status", sa.Text(), server_default="waiting"))
    if "retry_count" not in columns:
        op.add_column("posts", sa.Column("retry_count", sa.Integer(), server_default="0"))
    if "error_message" not in columns:
        op.add_column("posts", sa.Column("error_message", sa.Text()))
    if "scheduled_for" not in columns:
        op.add_column("posts", sa.Column("scheduled_for", sa.Text()))
    if "job_id" not in columns:
        op.add_column("posts", sa.Column("job_id", sa.Text()))


def downgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
    ).fetchone()
    if not exists:
        return
    res = conn.execute(sa.text("PRAGMA table_info(posts)")).fetchall()
    columns = [r[1] for r in res]
    for col in ["job_id", "scheduled_for", "error_message", "retry_count", "status"]:
        if col in columns:
            op.drop_column("posts", col)
