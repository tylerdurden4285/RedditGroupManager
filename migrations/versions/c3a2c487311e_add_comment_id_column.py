from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = 'c3a2c487311e'
down_revision: Union[str, None] = '4c19cde03134'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add comment_id column to posts table if missing."""
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
    ).fetchone()
    if not exists:
        return
    res = conn.execute(sa.text("PRAGMA table_info(posts)")).fetchall()
    columns = [r[1] for r in res]
    if "comment_id" not in columns:
        op.add_column("posts", sa.Column("comment_id", sa.Text()))


def downgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
    ).fetchone()
    if not exists:
        return
    res = conn.execute(sa.text("PRAGMA table_info(posts)")).fetchall()
    columns = [r[1] for r in res]
    if "comment_id" in columns:
        op.drop_column("posts", "comment_id")
