import httpx

from tender_telegram_bot.clients.tender_api_client import TenderApiClient


def _patch(monkeypatch, handler):
    api = TenderApiClient("http://test")
    monkeypatch.setattr(
        api, "_client", lambda: httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")
    )
    return api


def test_get_top(monkeypatch):
    def handler(req):
        assert req.url.path == "/api/tenders/top"
        return httpx.Response(200, json=[{"tender": {"id": "a"}, "score": None}])

    api = _patch(monkeypatch, handler)
    assert api.get_top()[0]["tender"]["id"] == "a"


def test_get_score_404_returns_none(monkeypatch):
    def handler(req):
        return httpx.Response(404, json={"detail": "no score"})

    api = _patch(monkeypatch, handler)
    assert api.get_score("t1") is None


def test_post_action(monkeypatch):
    captured = {}

    def handler(req):
        import json

        captured.update(json.loads(req.content))
        assert req.url.path == "/api/tenders/t1/actions"
        return httpx.Response(201, json={"id": "act1", "action": "interested"})

    api = _patch(monkeypatch, handler)
    out = api.post_action("t1", "interested", actor="telegram:5")
    assert out["action"] == "interested"
    assert captured["action"] == "interested"
    assert captured["actor"] == "telegram:5"
