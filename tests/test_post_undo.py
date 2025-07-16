from reddit_manager.services.reddit_service import RedditService
from reddit_manager.services.group_service import GroupService
from reddit_manager.utils.db import init_db
from flask import Flask


def _create_post(group_manager):
    post_data = {
        "subreddit": "python",
        "title": "T",
        "content": "B",
        "created_at": group_manager.get_current_timestamp(),
        "post_id": "pid",
        "post_url": "url",
        "post_type": "text",
        "comment": "c",
        "comment_id": "cid",
        "campaign": "camp",
    }
    return group_manager.save_post(post_data)


def test_undo_post_deletes_and_marks(app, group_manager, monkeypatch):
    with app.app_context():
        pid = _create_post(group_manager)
        called = {"post": None, "comment": None}
        order = []

        def del_post(self, sid):
            order.append("post")
            called["post"] = sid

        def del_comment(self, cid):
            order.append("comment")
            called["comment"] = cid

        monkeypatch.setattr(RedditService, "delete_post", del_post)
        monkeypatch.setattr(RedditService, "delete_comment", del_comment)

        assert group_manager.undo_post(pid)
        assert called["post"] == "pid"
        assert called["comment"] == "cid"
        assert order == ["comment", "post"]
        row = group_manager.get_post(pid)
        assert row["status"] == "undone"


def test_undo_post_endpoint(app, group_manager, monkeypatch):
    with app.app_context():
        pid = _create_post(group_manager)
        monkeypatch.setattr(RedditService, "delete_post", lambda self, sid: None)
        monkeypatch.setattr(RedditService, "delete_comment", lambda self, cid: None)
        client = app.test_client()
        resp = client.post(f"/posts/{pid}/undo")
        assert resp.status_code == 302
        assert group_manager.get_post(pid)["status"] == "undone"


def test_undo_post_failure_marks_failed(app, group_manager, monkeypatch):
    with app.app_context():
        pid = _create_post(group_manager)

        def raise_error(*args, **kwargs):
            raise Exception("boom")

        monkeypatch.setattr(RedditService, "delete_post", raise_error)
        monkeypatch.setattr(RedditService, "delete_comment", raise_error)

        assert not group_manager.undo_post(pid)
        row = group_manager.get_post(pid)
        assert row["status"] == "failed"
        assert "Undo failed" in row["error_message"]


def test_undo_post_no_app_context(tmp_path, monkeypatch):
    app = Flask("test")
    db_path = tmp_path / "test.db"
    app.config["DATABASE_PATH"] = str(db_path)
    with app.app_context():
        init_db(app)
        from reddit_manager.config.settings import Settings
        service = GroupService(Settings())
        pid = _create_post(service)

    def get_conn():
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    monkeypatch.setattr("reddit_manager.services.group_service.get_connection", get_conn)
    monkeypatch.setattr(RedditService, "delete_post", lambda self, sid: None)
    monkeypatch.setattr(RedditService, "delete_comment", lambda self, cid: None)

    assert service.undo_post(pid)
    with app.app_context():
        row = service.get_post(pid)
        assert row["status"] == "undone"


def test_undo_post_cancels_jobs(app, group_manager, monkeypatch):
    with app.app_context():
        pid = _create_post(group_manager)
        
        group_manager.get_post_job_ids(pid)
        from reddit_manager.utils.db import get_connection
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO post_check_jobs (post_id, job_id) VALUES (?, ?)",
                (pid, "j1"),
            )
            conn.execute(
                "INSERT INTO post_check_jobs (post_id, job_id) VALUES (?, ?)",
                (pid, "j2"),
            )

        calls = []

        class DummyScheduler:
            def cancel(self, job_id):
                calls.append(job_id)

        monkeypatch.setattr(
            "reddit_manager.tasks.post_tasks.scheduler", DummyScheduler()
        )
        monkeypatch.setattr(RedditService, "delete_post", lambda self, sid: None)
        monkeypatch.setattr(
            RedditService, "delete_comment", lambda self, cid: None
        )

        assert group_manager.undo_post(pid)

        assert set(calls) == {"j1", "j2"}
        with get_connection() as conn:
            remaining = conn.execute(
                "SELECT * FROM post_check_jobs WHERE post_id = ?", (pid,)
            ).fetchall()
        assert remaining == []
        assert group_manager.get_post(pid)["status"] == "undone"
