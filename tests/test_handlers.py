import asyncio
from unittest.mock import AsyncMock, MagicMock

from tender_telegram_bot.bot import handlers


def _fake_update(callback_data: str):
    query = MagicMock()
    query.data = callback_data
    query.from_user = MagicMock(id=42)
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    return update, query


def test_on_action_records_outcome(monkeypatch):
    calls = {}

    class FakeClient:
        def record_decision(self, tender_id, decision, outcome, actor=None):
            calls["decision"] = (tender_id, decision, outcome, actor)

        def post_action(self, *a, **k):
            calls["action"] = (a, k)

    monkeypatch.setattr(handlers, "TenderApiClient", FakeClient)
    update, query = _fake_update("action:res_ganada:t1")
    asyncio.run(handlers.on_action(update, None))

    assert calls["decision"] == ("t1", "GO", "ganada", "telegram:42")
    assert "action" not in calls  # no debe usar post_action para un resultado
    query.answer.assert_awaited()


def test_on_action_records_plain_action(monkeypatch):
    calls = {}

    class FakeClient:
        def record_decision(self, *a, **k):
            calls["decision"] = (a, k)

        def post_action(self, tender_id, action, actor=None):
            calls["action"] = (tender_id, action, actor)

    monkeypatch.setattr(handlers, "TenderApiClient", FakeClient)
    update, query = _fake_update("action:interested:t2")
    asyncio.run(handlers.on_action(update, None))

    assert calls["action"] == ("t2", "interested", "telegram:42")
    assert "decision" not in calls


def test_on_action_prepare_offer(monkeypatch):
    calls = {}

    class FakeClient:
        def generate_offer_drafts(self, tender_id):
            calls["gen"] = tender_id

        def post_action(self, *a, **k):
            calls["action"] = True

        def record_decision(self, *a, **k):
            calls["decision"] = True

    monkeypatch.setattr(handlers, "TenderApiClient", FakeClient)
    update, query = _fake_update("action:prepare_offer:t9")
    asyncio.run(handlers.on_action(update, None))

    assert calls["gen"] == "t9"
    assert "action" not in calls and "decision" not in calls
    query.answer.assert_awaited()
