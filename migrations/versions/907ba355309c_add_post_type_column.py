from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = '907ba355309c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add post_type column to posts table if missing."""
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
    ).fetchone()
    if not exists:
        return
    res = conn.execute(sa.text("PRAGMA table_info(posts)")).fetchall()
    columns = [r[1] for r in res]
    if "post_type" not in columns:
        op.add_column(
            "posts",
            sa.Column("post_type", sa.Text(), server_default="text"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
    ).fetchone()
    if not exists:
        return
    res = conn.execute(sa.text("PRAGMA table_info(posts)")).fetchall()
    columns = [r[1] for r in res]
    if "post_type" in columns:
        op.drop_column("posts", "post_type")
