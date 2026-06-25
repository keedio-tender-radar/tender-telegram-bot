from tender_telegram_bot.bot import messages
from tests.conftest import tender_with_score


def test_format_item():
    out = messages.format_item(tender_with_score("a", 92, "go"), index=1)
    assert out.startswith("1. Plataforma de datos")
    assert "92/100 · GO" in out
    assert "620.000 EUR" in out
    assert "2026-07-15" in out


def test_daily_digest_with_items(items):
    out = messages.format_daily_digest(items)
    assert "Resumen diario" in out
    assert "TOP oportunidades" in out
    assert "1. Plataforma de datos" in out
    assert "2. Integración de APIs" in out


def test_daily_digest_empty():
    out = messages.format_daily_digest([])
    assert "no hay oportunidades" in out.lower()


def test_daily_digest_with_stats(items):
    out = messages.format_daily_digest(items, stats={"analyzed": 184, "relevant": 9})
    assert "Analizadas: 184" in out


def test_format_urgent():
    out = messages.format_urgent(tender_with_score("a", 87, "revisar"))
    assert "urgente" in out.lower()
    assert "Score 87/100 (REVISAR)" in out


def test_format_detail_with_score():
    tw = tender_with_score("a", 92, "go")
    out = messages.format_tender_detail(tw["tender"], tw["score"])
    assert "Plataforma de datos" in out
    assert "92/100 · GO" in out
    assert "➕ CPV preferido" in out
    assert "72300000" in out


def test_format_detail_without_score():
    tw = tender_with_score("a", score=None)
    out = messages.format_tender_detail(tw["tender"], None)
    assert "Score" not in out


def test_format_answer():
    from tender_telegram_bot.bot.messages import format_answer

    out = format_answer(
        "¿Solvencia?",
        {"answer": "Tres proyectos.", "backend": "fake+llm", "sources": [{"page": 1}]},
    )
    assert "¿Solvencia?" in out
    assert "Tres proyectos." in out
    assert "fake+llm" in out
