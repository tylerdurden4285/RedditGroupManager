import datetime
import json
from pathlib import Path
from reddit_manager.services.group_service import Scheduler


def _schedule_image_post(app, group_manager, tmp_file, monkeypatch):
    class DummyScheduler:
        def enqueue_at(self, dt, func, post_id):
            class Job:
                id = "jid"
            return Job()

    monkeypatch.setattr(Scheduler, "__init__", lambda self, queue_name, connection: None)
    monkeypatch.setattr(Scheduler, "enqueue_at", DummyScheduler().enqueue_at)

    run_at = datetime.datetime.now(group_manager.timezone) + datetime.timedelta(minutes=10)
    post_data = {
        "subreddit": "python",
        "title": "T",
        "content": str(tmp_file),
        "image_path": str(tmp_file),
        "post_type": "image",
    }
    return group_manager.create_scheduled_post(post_data, run_at)


def test_preview_route_returns_file(app, group_manager, monkeypatch, tmp_path):
    with app.app_context():
        temp_dir = Path(app.instance_path) / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        fpath = temp_dir / "test.txt"
        fpath.write_text("hello")
        pid = _schedule_image_post(app, group_manager, fpath, monkeypatch)
        client = app.test_client()
        resp = client.get(f"/posts/preview/{fpath.name}")
        assert resp.status_code == 200
        assert resp.data == b"hello"


def test_modal_json_includes_preview_url(app, group_manager, monkeypatch, tmp_path):
    with app.app_context():
        temp_dir = Path(app.instance_path) / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        fpath = temp_dir / "img.jpg"
        fpath.write_text("data")
        pid = _schedule_image_post(app, group_manager, fpath, monkeypatch)
        client = app.test_client()
        resp = client.get("/posts/")
        html = resp.get_data(as_text=True)
        assert f"/posts/preview/{fpath.name}" in html
        resp = client.get(f"/posts/statuses?ids={pid}")
        data = json.loads(resp.get_data(as_text=True))
        found = next((p for p in data if p["id"] == pid), None)
        assert found and found["preview_url"].endswith(f"/posts/preview/{fpath.name}")
