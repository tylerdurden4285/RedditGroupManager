from types import SimpleNamespace
from click.testing import CliRunner
from pathlib import Path
import importlib.util

MODULE_PATH = Path(__file__).resolve().parents[1] / "purge-history.py"
spec = importlib.util.spec_from_file_location("purge_history", MODULE_PATH)
purge_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(purge_script)


def setup_service(num_subs=2, num_comments=3):
    class DummyItem:
        def __init__(self, id):
            self.id = id
            self.deleted = False
        def delete(self):
            self.deleted = True

    submissions = [DummyItem(f"s{i}") for i in range(num_subs)]
    comments = [DummyItem(f"c{i}") for i in range(num_comments)]

    class DummyUser:
        def __init__(self):
            self.submissions = SimpleNamespace(new=lambda limit=None: (s for s in submissions))
            self.comments = SimpleNamespace(new=lambda limit=None: (c for c in comments))

    dummy_user = DummyUser()
    dummy_reddit = SimpleNamespace(user=SimpleNamespace(me=lambda: dummy_user))

    def purge_user_history():
        for com in dummy_user.comments.new():
            com.delete()
        for sub in dummy_user.submissions.new():
            sub.delete()

    service = SimpleNamespace(reddit=dummy_reddit, purge_user_history=purge_user_history)
    return service, submissions, comments


def test_script_progress(monkeypatch):
    service, subs, comments = setup_service(2, 1)
    monkeypatch.setattr(purge_script, "RedditService", lambda settings: service)
    runner = CliRunner()
    result = runner.invoke(purge_script.main, input="y\n")
    total = len(subs) + len(comments)
    assert result.exit_code == 0
    assert result.output.count("Checking:") == total
    assert result.output.count("Deleting:") == total
    assert result.output.count("Purged:") == total


def test_script_prompt_abort(monkeypatch):
    service, _, _ = setup_service()
    called = False
    def no_call():
        nonlocal called
        called = True
    service.purge_user_history = no_call
    monkeypatch.setattr(purge_script, "RedditService", lambda settings: service)
    runner = CliRunner()
    result = runner.invoke(purge_script.main, input="n\n")
    assert "Aborted" in result.output
    assert called is False
