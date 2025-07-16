from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'ea15cf0c73a1'
down_revision: Union[str, None] = '6cd196ddaaeb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add image_path column to posts table if missing."""
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
    ).fetchone()
    if not exists:
        return
    res = conn.execute(sa.text("PRAGMA table_info(posts)")).fetchall()
    cols = [r[1] for r in res]
    if 'image_path' not in cols:
        op.add_column('posts', sa.Column('image_path', sa.Text()))


def downgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
    ).fetchone()
    if not exists:
        return
    res = conn.execute(sa.text("PRAGMA table_info(posts)")).fetchall()
    cols = [r[1] for r in res]
    if 'image_path' in cols:
        op.drop_column('posts', 'image_path')
