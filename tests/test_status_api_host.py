import requests
from reddit_manager import create_app


def test_status_api_uses_internal_host(monkeypatch):
    monkeypatch.setenv("API_STATUS_HOST", "innerhost")
    monkeypatch.setenv("API_PORT", "1234")

    called = {}

    def fake_get(url, timeout=2, headers=None):
        called["url"] = url
        class Resp:
            status_code = 200
        return Resp()

    monkeypatch.setattr(requests, "get", fake_get)
    app = create_app("testing")
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()
    resp = client.get("/status")
    assert resp.status_code == 200
    assert called["url"] == "http://innerhost:1234/api/v1/groups"
