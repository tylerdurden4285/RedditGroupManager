import types
from flask import url_for
from reddit_manager.tasks.post_tasks import process_post, _ensure_status_columns


def _create_post(group_manager, status="failed"):
    post_data = {
        "subreddit": "python",
        "title": "T",
        "content": "B",
        "created_at": group_manager.get_current_timestamp(),
        "post_id": "pid",
        "post_url": "url",
        "post_type": "text",
        "campaign": "camp",
        "status": status,
    }
    return group_manager.save_post(post_data)


def test_repost_posts_updates_status(group_manager):
    group_manager._run_migrations()
    _create_post(group_manager)
    _ensure_status_columns()
    ids = []
    for _ in range(3):
        ids.append(_create_post(group_manager, status="undone"))

    count = group_manager.repost_posts(ids)

    assert count == len(ids)
    for pid in ids:
        row = group_manager.get_post(pid)
        assert row["status"] == "processing"


def test_repost_selected_route(app, monkeypatch):
    with app.app_context():
        app.group_manager._run_migrations()
        _create_post(app.group_manager)
        _ensure_status_columns()
        p1 = _create_post(app.group_manager, status="undone")
        p2 = _create_post(app.group_manager, status="undone")

        enqueued = []

        def fake_enqueue(func, pid):
            enqueued.append((func, pid))
            return types.SimpleNamespace(id="1")

        app.queue = types.SimpleNamespace(enqueue=fake_enqueue)

        client = app.test_client()
        resp = client.post(
            "/posts/repost-selected",
            data={"post_ids": f"{p1},{p2}"},
        )

        assert resp.status_code == 302
        assert len(enqueued) == 2
        assert all(job[0] is process_post for job in enqueued)
        with app.test_request_context():
            assert resp.headers["Location"].endswith(url_for("posts_history.post_history"))

