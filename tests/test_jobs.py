from tender_telegram_bot.jobs.daily_summary_job import build_daily_summary, build_urgent_alerts


class FakeApi:
    def __init__(self, top=None, urgent=None):
        self._top = top or []
        self._urgent = urgent or []

    def get_top(self, limit=None):
        return self._top

    def get_urgent(self, days=None):
        return self._urgent


def test_build_daily_summary(items):
    summary = build_daily_summary(FakeApi(top=items))
    # cabecera CORTA (no repite la lista completa)
    assert "oportunidad" in summary["header"].lower()
    assert "1. Plataforma" not in summary["header"]
    assert [i["tender_id"] for i in summary["items"]] == ["a", "b"]
    # cada item lleva sus botones inline + enlace al panel (ficha)
    assert summary["items"][0]["buttons"][0][0][1] == "action:interested:a"
    assert "/tenders/a" in summary["items"][0]["text"]


def test_build_daily_summary_empty():
    summary = build_daily_summary(FakeApi(top=[]))
    assert summary["items"] == []
    assert "no hay oportunidades" in summary["header"].lower()


def test_build_urgent_alerts(items):
    alerts = build_urgent_alerts(FakeApi(urgent=items))
    assert len(alerts) == 2
    assert "urgente" in alerts[0]["text"].lower()
    assert alerts[0]["tender_id"] == "a"
