import pytest

from reddit_manager import create_app
from reddit_manager.utils.connection_check import check_connections


def test_check_connections_outputs(monkeypatch, capsys):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "dummy")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "dummy")
    monkeypatch.setenv("REDDIT_USER_AGENT", "dummy")
    monkeypatch.setenv("REDDIT_USERNAME", "dummy")
    monkeypatch.setenv("REDDIT_PASSWORD", "dummy")

    app_instance = create_app("testing")
    app_instance.debug = True

    class DummyReddit:
        def is_connected(self):
            return True

        def get_reddit_username(self):
            return "tester"

    class DummyGroupManager:
        def list_groups(self):
            return []

    app_instance.reddit = DummyReddit()
    app_instance.group_manager = DummyGroupManager()

    output = capsys.readouterr().out
    result = check_connections(app_instance)
    output = capsys.readouterr().out

    assert result is True
