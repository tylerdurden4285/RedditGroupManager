import types
from flask import Flask
from types import SimpleNamespace

from reddit_manager.tasks.post_tasks import check_moderation_status
from reddit_manager.services.group_service import GroupService
from reddit_manager.utils.db import init_db, get_connection
from reddit_manager.config.settings import Settings


def test_check_moderation_status_marks_posted(tmp_path, monkeypatch):
    app = Flask("test")
    db_path = tmp_path / "db.db"
    app.config["DATABASE_PATH"] = str(db_path)
    with app.app_context():
        init_db(app)
        service = GroupService(Settings())
        app.group_manager = service
        ts = service.get_current_timestamp()
        post_id = service.save_post({
            "subreddit": "python",
            "title": "T",
            "created_at": ts,
            "post_id": "pid",
            "post_url": "url",
        })

        class DummySubmission:
            approved = False
            removed_by_category = None

            def _fetch(self):
                pass

        class DummyReddit:
            def submission(self, id):
                assert id == "sid"
                return DummySubmission()

        dummy_service = SimpleNamespace(reddit=DummyReddit())
        monkeypatch.setattr(app, "reddit", dummy_service, raising=False)

        check_moderation_status(post_id, "sid", 1, 5)

        with get_connection() as conn:
            status = conn.execute("SELECT status FROM posts WHERE id = ?", (post_id,)).fetchone()[0]
        assert status == "posted"


def _setup_app(tmp_path):
    app = Flask("test")
    db_path = tmp_path / "db.db"
    app.config["DATABASE_PATH"] = str(db_path)
    with app.app_context():
        init_db(app)
        service = GroupService(Settings())
        app.group_manager = service
        ts = service.get_current_timestamp()
        post_id = service.save_post({
            "subreddit": "python",
            "title": "T",
            "created_at": ts,
            "post_id": "pid",
            "post_url": "url",
        })
    return app, service, post_id


def test_check_moderation_status_marks_awaiting(tmp_path, monkeypatch):
    app, service, post_id = _setup_app(tmp_path)
    with app.app_context():
        class DummySubmission:
            approved = False
            removed_by_category = "moderator"

            def _fetch(self):
                pass

        class DummyReddit:
            def submission(self, id):
                assert id == "sid"
                return DummySubmission()

        dummy_service = SimpleNamespace(reddit=DummyReddit())
        monkeypatch.setattr(app, "reddit", dummy_service, raising=False)

        check_moderation_status(post_id, "sid", 1, 5)

        with get_connection() as conn:
            status = conn.execute("SELECT status FROM posts WHERE id = ?", (post_id,)).fetchone()[0]
        assert status == "awaiting"


def test_check_moderation_status_marks_filtered(tmp_path, monkeypatch):
    app, service, post_id = _setup_app(tmp_path)
    with app.app_context():
        class DummySubmission:
            approved = False
            removed_by_category = "reddit"

            def _fetch(self):
                pass

        class DummyReddit:
            def submission(self, id):
                assert id == "sid"
                return DummySubmission()

        dummy_service = SimpleNamespace(reddit=DummyReddit())
        monkeypatch.setattr(app, "reddit", dummy_service, raising=False)

        check_moderation_status(post_id, "sid", 1, 5)

        with get_connection() as conn:
            status = conn.execute("SELECT status FROM posts WHERE id = ?", (post_id,)).fetchone()[0]
        assert status == "filtered"


def test_check_moderation_status_skips_undone(tmp_path, monkeypatch):
    """Ensure undone posts remain unchanged when checked."""
    app, service, post_id = _setup_app(tmp_path)
    with app.app_context():
        
        service.mark_post_undone(post_id, "undone")

        class DummySubmission:
            approved = False
            removed_by_category = "reddit"

            def _fetch(self):
                pass

        class DummyReddit:
            def submission(self, id):
                assert id == "sid"
                return DummySubmission()

        dummy_service = SimpleNamespace(reddit=DummyReddit())
        monkeypatch.setattr(app, "reddit", dummy_service, raising=False)

        result = check_moderation_status(post_id, "sid", 1, 5)
        assert result is False

        with get_connection() as conn:
            status = conn.execute(
                "SELECT status FROM posts WHERE id = ?",
                (post_id,),
            ).fetchone()[0]
        assert status == "undone"


def test_check_moderation_status_skips_posted(tmp_path, monkeypatch):
    app, service, post_id = _setup_app(tmp_path)
    with app.app_context():
        with get_connection() as conn:
            conn.execute("UPDATE posts SET status = 'posted' WHERE id = ?", (post_id,))

        class DummySubmission:
            approved = False
            removed_by_category = "reddit"

            def _fetch(self):
                pass

        class DummyReddit:
            def submission(self, id):
                assert id == "sid"
                return DummySubmission()

        dummy_service = SimpleNamespace(reddit=DummyReddit())
        monkeypatch.setattr(app, "reddit", dummy_service, raising=False)

        result = check_moderation_status(post_id, "sid", 1, 5)
        assert result is False

        with get_connection() as conn:
            status = conn.execute(
                "SELECT status FROM posts WHERE id = ?",
                (post_id,),
            ).fetchone()[0]
        assert status == "posted"
