import os
import sqlite3
from flask import Flask
import pytest
from reddit_manager.services.reddit_service import RedditService
from reddit_manager.services.group_service import GroupService
from reddit_manager.utils.db import init_db
from reddit_manager.config.settings import Settings


def test_reddit_service_reload_from_env(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "id1")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "sec1")
    monkeypatch.setenv("REDDIT_USER_AGENT", "ua1")
    monkeypatch.setenv("REDDIT_USERNAME", "user1")
    monkeypatch.setenv("REDDIT_PASSWORD", "pass1")
    service = RedditService(Settings())
    assert service.reddit.config.client_id == "id1"
    assert service.reddit.config.username == "user1"

    monkeypatch.setenv("REDDIT_CLIENT_ID", "id2")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "sec2")
    monkeypatch.setenv("REDDIT_USER_AGENT", "ua2")
    monkeypatch.setenv("REDDIT_USERNAME", "user2")
    monkeypatch.setenv("REDDIT_PASSWORD", "pass2")

    service.reload_from_env()
    assert service.reddit.config.client_id == "id2"
    assert service.reddit.config.username == "user2"


def test_reddit_service_missing_env(monkeypatch):
    for var in [
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT",
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
    ]:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError):
        RedditService(Settings())


def test_reddit_service_reload_missing_env(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "id1")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "sec1")
    monkeypatch.setenv("REDDIT_USER_AGENT", "ua1")
    monkeypatch.setenv("REDDIT_USERNAME", "user1")
    monkeypatch.setenv("REDDIT_PASSWORD", "pass1")
    service = RedditService(Settings())

    monkeypatch.delenv("REDDIT_PASSWORD", raising=False)
    with pytest.raises(ValueError):
        service.reload_from_env()


def test_group_service_reload_from_env(tmp_path):
    app = Flask("test")
    db1 = tmp_path / "db1.db"
    db2 = tmp_path / "db2.db"
    app.config["DATABASE_PATH"] = str(db1)
    ctx = app.app_context()
    ctx.push()
    init_db(app)
    service = GroupService(Settings())
    service.create_group("G1", "", [{"subreddit": "r1"}])

    app.config["DATABASE_PATH"] = str(db2)
    os.environ["DATABASE_PATH"] = str(db2)
    service.reload_from_env()
    service.create_group("G2", "", [{"subreddit": "r2"}])

    with sqlite3.connect(db1) as conn:
        rows = conn.execute("SELECT name FROM groups").fetchall()
        names1 = [r[0] for r in rows]
    with sqlite3.connect(db2) as conn:
        rows = conn.execute("SELECT name FROM groups").fetchall()
        names2 = [r[0] for r in rows]
    ctx.pop()

    assert "G1" in names1
    assert "G2" not in names1
    assert "G2" in names2
