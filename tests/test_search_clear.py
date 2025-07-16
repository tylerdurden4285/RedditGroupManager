import pytest
from flask import url_for


def _create_post(group_manager, title):
    post_data = {
        "subreddit": "python",
        "title": title,
        "content": title,
        "created_at": group_manager.get_current_timestamp(),
        "post_id": title,
        "post_url": f"url_{title}",
        "post_type": "text",
        "campaign": "camp",
    }
    return group_manager.save_post(post_data)


def test_search_clear_returns_all_posts(app, group_manager):
    with app.app_context():
        _create_post(group_manager, "foo123")
        _create_post(group_manager, "bar456")

        client = app.test_client()

        resp = client.get("/posts/", query_string={"search": "foo123"})
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "foo123" in html
        assert "bar456" not in html

        resp = client.get("/posts/", query_string={"search": ""})
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "foo123" in html
        assert "bar456" in html
