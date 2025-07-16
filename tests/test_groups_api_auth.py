from reddit_manager import create_app


def test_groups_requires_auth(monkeypatch):
    monkeypatch.setenv('AUTH_KEY', 'testkey')
    app = create_app('testing')
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    with app.app_context():
        resp = client.get('/api/v1/groups/')
        assert resp.status_code == 403

        resp = client.get('/api/v1/groups/', headers={'Authorization': 'testkey'})
        assert resp.status_code == 200
