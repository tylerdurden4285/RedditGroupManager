import pytest


def test_history_displays_waiting_and_processing(app, group_manager):
    with app.app_context():
        ts = group_manager.get_current_timestamp()
        group_manager.create_processing_post({
            "subreddit": "python",
            "title": "processing",
            "created_at": ts,
            "post_id": "pid1",
            "post_url": "url1",
            "campaign": "c",
        })
        group_manager.save_post({
            "subreddit": "python",
            "title": "waiting",
            "created_at": ts,
            "post_id": "pid2",
            "post_url": "url2",
            "campaign": "c",
        })
        client = app.test_client()
        resp = client.get("/posts/")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Processing..." in html
        assert "Please Wait..." in html
        assert "See on Reddit" not in html
