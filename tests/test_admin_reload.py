from reddit_manager import create_app
from reddit_manager.utils.db import init_db
from reddit_manager.config.settings import Settings
import os


def setup_app(monkeypatch, tmp_path):
    os.environ.setdefault('REDDIT_CLIENT_ID', 'dummy')
    os.environ.setdefault('REDDIT_CLIENT_SECRET', 'dummy')
    os.environ.setdefault('REDDIT_USER_AGENT', 'dummy')
    os.environ.setdefault('REDDIT_USERNAME', 'dummy')
    os.environ.setdefault('REDDIT_PASSWORD', 'dummy')
    db_file = tmp_path / 'test.db'
    monkeypatch.setenv('DATABASE_PATH', str(db_file))
    monkeypatch.setenv('USER_DB_PATH', str(db_file))
    app = create_app('testing')
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        init_db(app)
    return app


def test_admin_reload_requires_auth(monkeypatch, tmp_path):
    monkeypatch.setenv('AUTH_KEY', 'key')
    app = setup_app(monkeypatch, tmp_path)
    client = app.test_client()

    response = client.post('/admin/reload')
    assert response.status_code == 403

    response = client.post('/admin/reload', headers={'Authorization': 'key'})
    assert response.status_code == 200


def test_admin_reload_updates_services(monkeypatch, tmp_path):
    monkeypatch.setenv('AUTH_KEY', 'key')
    monkeypatch.setenv('REDDIT_CLIENT_ID', 'id1')
    app = setup_app(monkeypatch, tmp_path)
    client = app.test_client()

    assert app.reddit.reddit.config.client_id == 'id1'
    monkeypatch.setenv('REDDIT_CLIENT_ID', 'id2')
    response = client.post('/admin/reload', headers={'Authorization': 'key'})
    assert response.status_code == 200
    assert app.reddit.reddit.config.client_id == 'id2'
