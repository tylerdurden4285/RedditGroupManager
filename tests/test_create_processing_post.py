import pytest
from flask import Flask

from reddit_manager.services.group_service import GroupService
from reddit_manager.utils.db import init_db, get_connection
from reddit_manager.config.settings import Settings


@pytest.fixture()
def group_service(tmp_path):
    app = Flask("test")
    app.config["DATABASE_PATH"] = str(tmp_path / "proc.db")
    ctx = app.app_context()
    ctx.push()
    init_db(app)
    service = GroupService(Settings())
    yield service
    ctx.pop()


def test_create_processing_post_creates_row(group_service):
    post_data = {
        "subreddit": "python",
        "title": "Title",
        "created_at": group_service.get_current_timestamp(),
        "post_id": "pid",
        "post_url": "url",
        "campaign": "camp",
    }
    post_id = group_service.create_processing_post(post_data)
    assert isinstance(post_id, int)

    with get_connection() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        assert row is not None
        assert row["status"] == "processing"
        columns = {r[1] for r in conn.execute("PRAGMA table_info(posts)")}

    expected = {
        "id",
        "subreddit",
        "title",
        "content",
        "image_path",
        "created_at",
        "post_id",
        "post_url",
        "flair_id",
        "flair_text",
        "post_type",
        "comment",
        "comment_id",
        "status",
        "campaign",
        "retry_count",
        "error_message",
        "scheduled_for",
        "job_id",
        "scheduled_at",
    }
    assert expected.issubset(columns)
