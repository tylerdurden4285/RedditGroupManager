from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '8b1f8cf1d9ab'
down_revision: Union[str, None] = '26f661cf3cce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Add campaign column to posts table if missing."""
    conn = op.get_bind()
    exists = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")).fetchone()
    if not exists:
        return
    res = conn.execute(sa.text("PRAGMA table_info(posts)")).fetchall()
    columns = [r[1] for r in res]
    if 'campaign' not in columns:
        op.add_column('posts', sa.Column('campaign', sa.Text()))


def downgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")).fetchone()
    if not exists:
        return
    res = conn.execute(sa.text("PRAGMA table_info(posts)")).fetchall()
    columns = [r[1] for r in res]
    if 'campaign' in columns:
        op.drop_column('posts', 'campaign')
