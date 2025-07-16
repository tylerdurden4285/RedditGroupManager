import pytest
from reddit_manager import create_app


def test_flair_selector_handles_generic_exception(monkeypatch):
    monkeypatch.setenv('REDDIT_CLIENT_ID', 'dummy')
    monkeypatch.setenv('REDDIT_CLIENT_SECRET', 'dummy')
    monkeypatch.setenv('REDDIT_USER_AGENT', 'dummy')
    monkeypatch.setenv('REDDIT_USERNAME', 'dummy')
    monkeypatch.setenv('REDDIT_PASSWORD', 'dummy')
    monkeypatch.setenv('AUTH_KEY', 'testkey')
    flask_app = create_app("testing")
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = flask_app.test_client()

    def mock_get_flairs(subreddit_name):
        raise Exception("boom")

    monkeypatch.setattr(flask_app.reddit, "get_flairs", mock_get_flairs)

    with flask_app.app_context():
        response = client.get("/api/v1/reddit/flairs-html/testsub")
        assert response.status_code == 200
        assert b"Error loading flairs" in response.data


def test_flair_selector_allowed_without_auth(monkeypatch):
    monkeypatch.setenv('REDDIT_CLIENT_ID', 'dummy')
    monkeypatch.setenv('REDDIT_CLIENT_SECRET', 'dummy')
    monkeypatch.setenv('REDDIT_USER_AGENT', 'dummy')
    monkeypatch.setenv('REDDIT_USERNAME', 'dummy')
    monkeypatch.setenv('REDDIT_PASSWORD', 'dummy')
    monkeypatch.setenv('AUTH_KEY', 'testkey')
    flask_app = create_app("testing")
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = flask_app.test_client()

    with flask_app.app_context():
        response = client.get("/api/v1/reddit/flairs-html/testsub")
        assert response.status_code == 200
