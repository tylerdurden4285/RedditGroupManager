import datetime
from reddit_manager.services.group_service import Scheduler
from reddit_manager.utils.db import get_connection


def test_update_scheduled_post(app, group_manager, monkeypatch):
    with app.app_context():
        calls = {"cancel": None, "enqueue": None}

        class DummyScheduler:
            def __init__(self, *a, **k):
                pass
            def cancel(self, jid):
                calls["cancel"] = jid
            def enqueue_at(self, dt, func, pid):
                calls["enqueue"] = (dt, pid)
                class Job:
                    id = "new"
                return Job()

        monkeypatch.setattr(Scheduler, "__init__", lambda self, queue_name, connection: None)
        monkeypatch.setattr(Scheduler, "enqueue_at", DummyScheduler().enqueue_at)
        monkeypatch.setattr(Scheduler, "cancel", DummyScheduler().cancel)

        run_at = datetime.datetime.now(group_manager.timezone) + datetime.timedelta(minutes=5)
        pid = group_manager.create_scheduled_post({"subreddit": "s", "title": "T", "content": "B", "campaign": "c"}, run_at)
        with get_connection() as conn:
            old = conn.execute("SELECT job_id FROM posts WHERE id = ?", (pid,)).fetchone()[0]
        assert old

        new_time = run_at + datetime.timedelta(minutes=10)
        assert group_manager.update_scheduled_post(pid, new_time)
        assert calls["cancel"] == old
        assert calls["enqueue"] and calls["enqueue"][1] == pid
        with get_connection() as conn:
            row = conn.execute("SELECT job_id, scheduled_for FROM posts WHERE id = ?", (pid,)).fetchone()
        assert row["job_id"] == "new"
        assert row["scheduled_for"].startswith(new_time.astimezone(group_manager.timezone).strftime("%Y-%m-%dT%H:%M"))


def test_update_overdue_post(app, group_manager, monkeypatch):
    with app.app_context():
        class DummyScheduler:
            def __init__(self, *a, **k):
                pass

            def cancel(self, jid):
                pass

            def enqueue_at(self, dt, func, pid):
                class Job:
                    id = "new2"

                return Job()

        monkeypatch.setattr(Scheduler, "__init__", lambda self, queue_name, connection: None)
        monkeypatch.setattr(Scheduler, "enqueue_at", DummyScheduler().enqueue_at)
        monkeypatch.setattr(Scheduler, "cancel", DummyScheduler().cancel)

        past_time = datetime.datetime.now(group_manager.timezone) - datetime.timedelta(minutes=5)
        pid = group_manager.create_scheduled_post({"subreddit": "s", "title": "T", "content": "B", "campaign": "c"}, past_time)
        group_manager.mark_overdue_scheduled_posts()

        new_time = datetime.datetime.now(group_manager.timezone) + datetime.timedelta(minutes=5)
        assert group_manager.update_scheduled_post(pid, new_time)
        with get_connection() as conn:
            row = conn.execute("SELECT status, scheduled_for FROM posts WHERE id = ?", (pid,)).fetchone()
        assert row["status"] == "scheduled"
        assert row["scheduled_for"].startswith(new_time.astimezone(group_manager.timezone).strftime("%Y-%m-%dT%H:%M"))


def test_delete_posts_cancels_jobs(app, group_manager, monkeypatch):
    with app.app_context():
        class DummyScheduler:
            def __init__(self, *a, **k):
                pass
            def enqueue_at(self, dt, func, pid):
                class Job:
                    id = "jid"
                return Job()
            def cancel(self, jid):
                calls.append(jid)

        calls = []
        monkeypatch.setattr(Scheduler, "__init__", lambda self, queue_name, connection: None)
        monkeypatch.setattr(Scheduler, "enqueue_at", DummyScheduler().enqueue_at)
        monkeypatch.setattr(Scheduler, "cancel", DummyScheduler().cancel)

        run_at = datetime.datetime.now(group_manager.timezone) + datetime.timedelta(minutes=5)
        pid = group_manager.create_scheduled_post({"subreddit": "s", "title": "T", "content": "B", "campaign": "c"}, run_at)
        assert group_manager.delete_posts([pid]) == 1
        assert calls == ["jid"]
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
        assert row is None
