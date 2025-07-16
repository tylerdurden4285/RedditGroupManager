import types
from reddit_manager.tasks.post_tasks import process_post, _ensure_status_columns
from reddit_manager.utils.db import get_connection


def _create_failed_post(group_manager):
    post_id = group_manager.save_post(
        {
            "subreddit": "python",
            "title": "T",
            "content": "B",
            "created_at": group_manager.get_current_timestamp(),
            "post_id": "pid",
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
    return post_id


def test_repost_post_endpoint(app, group_manager):
    with app.app_context():
        pid = _create_failed_post(group_manager)
        enqueued = []

        def fake_enqueue(func, *args, **kwargs):
            enqueued.append((func, args))
            class Job:
                id = "1"
            return Job()

        app.queue = types.SimpleNamespace(enqueue=fake_enqueue)
        client = app.test_client()
        resp = client.post(f"/posts/{pid}/repost")
        assert resp.status_code == 302
        assert group_manager.get_post(pid)["status"] == "processing"
        assert enqueued and enqueued[0][0] is process_post
        assert enqueued[0][1][0] == pid


def test_repost_selected_endpoint(app, group_manager):
    with app.app_context():
        pid1 = _create_failed_post(group_manager)
        pid2 = _create_failed_post(group_manager)
        enqueued = []

        def fake_enqueue(func, *args, **kwargs):
            enqueued.append(args[0])
            class Job:
                id = "1"
            return Job()

        app.queue = types.SimpleNamespace(enqueue=fake_enqueue)
        client = app.test_client()
        data = {"post_ids": f"{pid1},{pid2}"}
        resp = client.post("/posts/repost-selected", data=data)
        assert resp.status_code == 302
        assert set(enqueued) == {pid1, pid2}
        assert group_manager.get_post(pid1)["status"] == "processing"
        assert group_manager.get_post(pid2)["status"] == "processing"
