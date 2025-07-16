import datetime
from reddit_manager.utils.db import get_connection
from reddit_manager.services.group_service import GroupService
from reddit_manager.services.group_service import Scheduler
import types


def test_create_scheduled_post(app, group_manager, monkeypatch):
    with app.app_context():
        calls = {}

        class DummyScheduler:
            def enqueue_at(self, dt, func, post_id):
                calls["dt"] = dt
                calls["pid"] = post_id

                class Job:
                    id = "jid"

                return Job()

        monkeypatch.setattr(
            Scheduler, "__init__", lambda self, queue_name, connection: None
        )
        monkeypatch.setattr(Scheduler, "enqueue_at", DummyScheduler().enqueue_at)
        run_at = datetime.datetime.now(group_manager.timezone) + datetime.timedelta(
            minutes=10
        )
        post_data = {
            "subreddit": "python",
            "title": "T",
            "content": "B",
            "campaign": "camp",
        }
        pid = group_manager.create_scheduled_post(post_data, run_at)
        assert isinstance(pid, int)
        assert calls["pid"] == pid
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
            assert row["status"] == "scheduled"
            assert row["job_id"] == "jid"


def test_create_scheduled_post_naive_dt(app, group_manager, monkeypatch):
    with app.app_context():
        calls = {}

        class DummyScheduler:
            def enqueue_at(self, dt, func, post_id):
                calls["dt"] = dt
                calls["pid"] = post_id

                class Job:
                    id = "jid"

                return Job()

        monkeypatch.setattr(
            Scheduler, "__init__", lambda self, queue_name, connection: None
        )
        monkeypatch.setattr(Scheduler, "enqueue_at", DummyScheduler().enqueue_at)
        run_at = datetime.datetime.now() + datetime.timedelta(minutes=10)
        post_data = {
            "subreddit": "python",
            "title": "T",
            "content": "B",
            "campaign": "camp",
        }
        pid = group_manager.create_scheduled_post(post_data, run_at)
        assert isinstance(pid, int)
        assert calls["pid"] == pid
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
            assert row["status"] == "scheduled"
            assert row["job_id"] == "jid"
