import os
from importlib import reload
from fastapi import HTTPException
from reddit_manager.services.user_service import UserService
from reddit_manager.config.settings import Settings


def test_verify_token_looks_up_user(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    import api_main
    reload(api_main)
    service = UserService(Settings())
    service.set_api_key("alice", "token123")

    assert api_main.verify_token("token123") == "token123"
    try:
        api_main.verify_token("bad")
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        assert False, "Expected HTTPException"


def test_verify_token_accepts_env_key(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("AUTH_KEY", "envtoken")
    import api_main
    reload(api_main)

    
    assert api_main.verify_token("envtoken") == "envtoken"
