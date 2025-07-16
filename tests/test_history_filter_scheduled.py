import datetime
from reddit_manager.services.group_service import Scheduler


def test_history_filter_scheduled(app, group_manager, monkeypatch):
    with app.app_context():
        class DummyScheduler:
            def enqueue_at(self, dt, func, pid):
                class Job:
                    id = "jid"
                return Job()

        monkeypatch.setattr(Scheduler, "__init__", lambda self, queue_name, connection: None)
        monkeypatch.setattr(Scheduler, "enqueue_at", DummyScheduler().enqueue_at)

        run_at = datetime.datetime.now(group_manager.timezone) + datetime.timedelta(minutes=5)
        group_manager.create_scheduled_post(
            {"subreddit": "python", "title": "sched", "content": "B", "campaign": "c"},
            run_at,
        )
        group_manager.save_post(
            {
                "subreddit": "python",
                "title": "other",
                "created_at": group_manager.get_current_timestamp(),
                "post_id": "pid",
                "post_url": "url",
                "campaign": "c",
            }
        )

        client = app.test_client()
        resp = client.get("/posts/", query_string={"post_type": "scheduled"})
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Scheduled for" in html
        assert "other" not in html
