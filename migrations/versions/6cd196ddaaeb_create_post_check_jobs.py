from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '6cd196ddaaeb'
down_revision: Union[str, None] = '8b1f8cf1d9ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create post_check_jobs table if missing."""
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='post_check_jobs'")
    ).fetchone()
    if not exists:
        op.create_table(
            'post_check_jobs',
            sa.Column('post_id', sa.Integer(), nullable=False),
            sa.Column('job_id', sa.Text(), nullable=False),
        )


def downgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='post_check_jobs'")
    ).fetchone()
    if exists:
        op.drop_table('post_check_jobs')
