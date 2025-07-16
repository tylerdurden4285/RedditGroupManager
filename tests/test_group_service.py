import sqlite3
import os
import pytest
import datetime
from flask import Flask

from reddit_manager.services.group_service import GroupService, GroupServiceError, Scheduler
from reddit_manager.utils.db import init_db
from reddit_manager.config.settings import Settings


@pytest.fixture()
def group_service(tmp_path):
    app = Flask("test")
    db_path = str(tmp_path / "test.db")
    app.config["DATABASE_PATH"] = db_path
    os.environ["DATABASE_PATH"] = db_path
    ctx = app.app_context()
    ctx.push()
    init_db(app)
    service = GroupService(Settings())
    service._run_migrations()
    yield service
    ctx.pop()


def test_get_group_invalid_id_returns_none(group_service):
    assert group_service.get_group(9999) is None


def test_get_group_db_error(monkeypatch, group_service):
    import reddit_manager.services.group_service as gs

    def bad_connection():
        raise sqlite3.OperationalError("boom")

    monkeypatch.setattr(gs, "get_connection", bad_connection)

    with pytest.raises(GroupServiceError):
        group_service.get_group(1)


def test_migration_renames_name_column(tmp_path):
    app = Flask("test")
    db_path = str(tmp_path / "old.db")
    app.config["DATABASE_PATH"] = db_path
    os.environ["DATABASE_PATH"] = db_path
    ctx = app.app_context()
    ctx.push()

    from reddit_manager.utils.db import get_connection

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE group_subreddits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                flair_id TEXT,
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                UNIQUE(group_id, name)
            )
            """
        )
        conn.commit()

    service = GroupService(Settings())
    service._run_migrations()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(group_subreddits)")
        columns = [row[1] for row in cursor.fetchall()]

    ctx.pop()

    assert "subreddit" in columns
    assert "name" not in columns


def test_create_group_saves_flair_text(group_service):
    group_id = group_service.create_group(
        "MyGroup", "", [{"subreddit": "python", "flair_id": "42", "flair_text": "Cool"}]
    )
    group = group_service.get_group(group_id)
    assert group is not None
    assert group.subreddits[0].flair_text == "Cool"


def test_flair_text_persists_in_db(group_service):
    group_id = group_service.create_group(
        "DBGroup",
        "",
        [{"subreddit": "learnpython", "flair_id": "99", "flair_text": "Neat"}],
    )

    from reddit_manager.utils.db import get_connection

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT flair_text FROM group_subreddits WHERE group_id = ? AND subreddit = ?",
            (group_id, "learnpython"),
        )
        row = cursor.fetchone()

    assert row is not None
    assert row[0] == "Neat"


def test_save_post_creates_row(group_service):
    ts = group_service.get_current_timestamp()
    post_data = {
        "subreddit": "python",
        "title": "Hello",
        "content": "Body",
        "created_at": ts,
        "post_id": "abc123",
        "post_url": "https://reddit.com/r/python/comments/abc123",
        "flair_id": "flair1",
        "flair_text": "text1",
        "post_type": "text",
        "comment": "hi",
        "campaign": "testcamp",
    }
    post_id = group_service.save_post(post_data)
    assert isinstance(post_id, int)

    from reddit_manager.utils.db import get_connection

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()

    assert row is not None
    assert row["subreddit"] == "python"
    assert row["title"] == "Hello"
    assert row["post_id"] == "abc123"
    assert row["post_url"] == "https://reddit.com/r/python/comments/abc123"
    assert row["flair_id"] == "flair1"
    assert row["flair_text"] == "text1"
    assert row["post_type"] == "text"
    assert row["comment"] == "hi"
    assert row["comment_id"] is None
    assert row["status"] == "waiting"
    assert row["retry_count"] == 0


def test_save_post_creates_table_with_columns(group_service):
    post_data = {
        "subreddit": "python",
        "title": "Title",
        "created_at": group_service.get_current_timestamp(),
        "post_id": "id1",
        "post_url": "url1",
        "campaign": "camp",
    }
    group_service.save_post(post_data)

    from reddit_manager.utils.db import get_connection

    with get_connection() as conn:
        cursor = conn.execute("PRAGMA table_info(posts)")
        columns = {row[1] for row in cursor.fetchall()}

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
    }
    assert expected.issubset(columns)


def test_count_posts_returns_zero_when_no_posts(tmp_path):
    app = Flask("test")
    app.config["DATABASE_PATH"] = str(tmp_path / "count.db")
    ctx = app.app_context()
    ctx.push()
    init_db(app)
    service = GroupService(Settings())
    service._run_migrations()
    count = service.count_posts()
    ctx.pop()
    assert count == 0


def test_delete_posts_removes_only_requested(group_service):
    ids = []
    for i in range(3):
        post_data = {
            "subreddit": f"test{i}",
            "title": "T",
            "content": "B",
            "created_at": group_service.get_current_timestamp(),
            "post_id": str(i),
            "post_url": f"url{i}",
            "post_type": "text",
            "campaign": "c",
        }
        ids.append(group_service.save_post(post_data))

    deleted = group_service.delete_posts(ids[:2])
    assert deleted == 2
    remaining = group_service.get_recent_posts(limit=10)
    remaining_ids = [p["id"] for p in remaining]
    assert ids[0] not in remaining_ids
    assert ids[1] not in remaining_ids
    assert ids[2] in remaining_ids


def test_migrate_status_updates_rows(tmp_path):
    app = Flask("test")
    db_path = str(tmp_path / "mig.db")
    app.config["DATABASE_PATH"] = db_path
    os.environ["DATABASE_PATH"] = db_path
    ctx = app.app_context()
    ctx.push()
    init_db(app)

    from reddit_manager.utils.db import get_connection

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS posts")
        cursor.execute(
            """
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subreddit TEXT,
                title TEXT,
                content TEXT,
                created_at TEXT,
                post_id TEXT,
                post_url TEXT,
                status TEXT DEFAULT 'posted'
            )
            """
        )
        cursor.execute(
            "INSERT INTO posts (subreddit, title, created_at, post_id, post_url) VALUES ('s', 't', 'ts', 'pid', 'url')"
        )
        conn.commit()

    service = GroupService(Settings())
    service._run_migrations()

    with get_connection() as conn:
        status = conn.execute("SELECT status FROM posts").fetchone()[0]

    ctx.pop()

    assert status == "waiting"


def test_get_recent_posts_date_range(group_service):
    timestamps = [
        "2023-01-01T12:00:00+00:00",
        "2023-01-02T12:00:00+00:00",
        "2023-01-03T12:00:00+00:00",
    ]
    for i, ts in enumerate(timestamps):
        group_service.save_post(
            {
                "subreddit": f"sub{i}",
                "title": f"T{i}",
                "created_at": ts,
                "post_id": f"pid{i}",
                "post_url": f"url{i}",
                "post_type": "text",
            }
        )

    posts = group_service.get_recent_posts(start_date="2023-01-02", end_date="2023-01-02")
    assert len(posts) == 1
    assert posts[0]["created_at"].startswith("2023-01-02")

    posts = group_service.get_recent_posts(start_date="2023-01-02", end_date="2023-01-03")
    returned = {p["created_at"] for p in posts}
    assert returned == set(timestamps[1:])


def test_get_recent_posts_offset_and_count(group_service):
    timestamps = [
        "2023-01-01T12:00:00+00:00",
        "2023-01-02T12:00:00+00:00",
        "2023-01-03T12:00:00+00:00",
        "2023-01-04T12:00:00+00:00",
    ]
    for i, ts in enumerate(timestamps):
        group_service.save_post(
            {
                "subreddit": "s",
                "title": f"T{i}",
                "created_at": ts,
                "post_id": f"pid{i}",
                "post_url": f"url{i}",
                "post_type": "text",
            }
        )

    count = group_service.count_posts()
    assert count == len(timestamps)

    page1 = group_service.get_recent_posts(limit=2)
    page2 = group_service.get_recent_posts(limit=2, offset=2)

    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0]["id"] != page2[0]["id"]


def test_get_recent_posts_status_filter(group_service):
    ts = group_service.get_current_timestamp()
    group_service.save_post(
        {
            "subreddit": "s",
            "title": "scheduled",
            "created_at": ts,
            "post_id": "sid",
            "post_url": "surl",
            "status": "scheduled",
        }
    )
    group_service.save_post(
        {
            "subreddit": "s",
            "title": "posted",
            "created_at": ts,
            "post_id": "pid",
            "post_url": "purl",
            "status": "posted",
        }
    )

    posts = group_service.get_recent_posts(status="scheduled")
    assert len(posts) == 1
    assert posts[0]["status"] == "scheduled"


def test_repost_post_resets_fields(group_service):
    from reddit_manager.tasks.post_tasks import _ensure_status_columns
    from reddit_manager.utils.db import get_connection

    ts = "2023-01-01T00:00:00+00:00"
    post_id = group_service.save_post(
        {
            "subreddit": "python",
            "title": "T",
            "content": "B",
            "created_at": ts,
            "post_id": "abc",
            "post_url": "url",
            "comment_id": "cid",
            "status": "failed",
            "error_message": "boom",
        }
    )

    _ensure_status_columns()

    with get_connection() as conn:
        conn.execute(
            "UPDATE posts SET reddit_url = 'rurl' WHERE id = ?",
            (post_id,),
        )

    assert group_service.repost_post(post_id)
    row = group_service.get_post(post_id)
    assert row["status"] == "processing"
    assert row["post_id"] == ""
    assert row["comment_id"] == ""
    assert row["reddit_url"] == ""
    assert row["error_message"] is None
    assert row["created_at"] != ts


def test_mark_overdue_scheduled_posts(group_service, monkeypatch):
    class DummyScheduler:
        def __init__(self, *a, **k):
            pass

        def enqueue_at(self, dt, func, pid):
            class Job:
                id = "jid"

            return Job()

        def cancel(self, jid):
            calls.append(jid)

    monkeypatch.setattr(
        Scheduler, "__init__", lambda self, queue_name, connection: None
    )
    monkeypatch.setattr(Scheduler, "enqueue_at", DummyScheduler().enqueue_at)
    monkeypatch.setattr(Scheduler, "cancel", DummyScheduler().cancel)

    past_time = datetime.datetime.now(group_service.timezone) - datetime.timedelta(minutes=5)
    calls = []
    pid = group_service.create_scheduled_post({"subreddit": "s", "title": "T", "content": "B"}, past_time)
    assert isinstance(pid, int)

    row = group_service.get_post(pid)
    assert row["job_id"] == "jid"

    count = group_service.mark_overdue_scheduled_posts()
    assert count == 1
    assert calls == ["jid"]
    row = group_service.get_post(pid)
    assert row["status"] == "overdue"
    assert row["job_id"] is None


def test_fail_overdue_posts(group_service, monkeypatch):
    class DummyScheduler:
        def __init__(self, *a, **k):
            pass

        def enqueue_at(self, dt, func, pid):
            class Job:
                id = "jid2"

            return Job()

        def cancel(self, jid):
            pass

    monkeypatch.setattr(Scheduler, "__init__", lambda self, queue_name, connection: None)
    monkeypatch.setattr(Scheduler, "enqueue_at", DummyScheduler().enqueue_at)
    monkeypatch.setattr(Scheduler, "cancel", DummyScheduler().cancel)

    past_time = datetime.datetime.now(group_service.timezone) - datetime.timedelta(minutes=5)
    pid = group_service.create_scheduled_post({"subreddit": "s", "title": "T", "content": "B"}, past_time)
    group_service.mark_overdue_scheduled_posts()
    count = group_service.fail_overdue_posts()
    assert count == 1
    row = group_service.get_post(pid)
    assert row["status"] == "failed"

