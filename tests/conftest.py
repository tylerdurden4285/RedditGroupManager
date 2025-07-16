import pytest

import os
import tempfile
import base64
from dataclasses import dataclass
from types import SimpleNamespace

from reddit_manager import create_app
from reddit_manager.utils.db import init_db
from reddit_manager.config.settings import Settings

@pytest.fixture(scope='function')
def app(tmp_path):
    os.environ.setdefault('REDDIT_CLIENT_ID', 'dummy')
    os.environ.setdefault('REDDIT_CLIENT_SECRET', 'dummy')
    os.environ.setdefault('REDDIT_USER_AGENT', 'dummy')
    os.environ.setdefault('REDDIT_USERNAME', 'dummy')
    os.environ.setdefault('REDDIT_PASSWORD', 'dummy')
    db_file = tmp_path / "test.db"
    os.environ["DATABASE_PATH"] = str(db_file)
    os.environ["USER_DB_PATH"] = str(db_file)
    app = create_app("testing")
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, DATABASE_PATH=str(db_file), USER_DB_PATH=str(db_file))
    with app.app_context():
        init_db(app)
    return app

@pytest.fixture(scope='function')
def group_manager(app):
    return app.group_manager


@pytest.fixture
def add_user():
    from reddit_manager.services.user_service import UserService

    def _add(app, username="user", api_key="secret"):
        with app.app_context():
            UserService(Settings(), app).set_api_key(username, api_key)

    return _add
