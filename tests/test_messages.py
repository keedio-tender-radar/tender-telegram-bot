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


def test_format_reminder_urgency_and_expediente():
    from datetime import UTC, datetime, timedelta

    dl = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    tw = {
        "tender": {
            "id": "x", "title": "Servicios X", "deadline": dl,
            "budget_amount": 100000, "currency": "EUR",
        },
        "score": {"total": 85, "recommendation": "go"},
    }
    out = messages.format_reminder(tw, docs_ready=12)
    assert "🟠" in out and "en 2 días" in out  # umbral ≤3 días
    assert "Servicios X" in out
    assert "12 documento(s) listos" in out
    assert "sin preparar" in messages.format_reminder(tw, docs_ready=0)


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


def test_format_market_context():
    from tender_telegram_bot.bot.messages import format_market_context

    out = format_market_context(
        {"title": "Plataforma de datos"},
        {
            "cpv_division": "72",
            "sample_size": 4,
            "expected_baja": 0.38,
            "likely_winners": [{"supplier": "INETUM ESPAÑA, S.A.", "wins": 3, "avg_baja": 0.02}],
        },
    )
    assert "Mercado" in out
    assert "38.0%" in out
    assert "INETUM" in out


def test_format_market_context_empty():
    from tender_telegram_bot.bot.messages import format_market_context

    out = format_market_context({"title": "X"}, {"sample_size": 0})
    assert "Sin histórico" in out


def test_format_competitor_profile():
    from tender_telegram_bot.bot.messages import format_competitor_profile

    out = format_competitor_profile({
        "supplier": "INETUM ESPAÑA, S.A.",
        "wins": 4, "total_awarded": 4865126, "share": 0.022, "avg_baja": 0.025,
        "by_buyer": [{"buyer": "Órgano A", "awards": 2}],
        "by_cpv": [{"cpv_division": "72", "awards": 3}],
        "contracts": [{"title": "Soporte plataforma", "awarded_amount": 100000,
                       "award_date": "2026-05-01"}],
    })
    assert "INETUM" in out
    assert "Contratos: 4" in out
    assert "Órgano A" in out
    assert "Soporte plataforma" in out


def test_format_market_overview():
    from tender_telegram_bot.bot.messages import format_market_overview

    ov = {
        "awards": 120,
        "avg_baja": 0.402,
        "total_awarded": 233000000,
        "top_competitor": {"supplier": "INETUM", "wins": 3, "share": 0.32},
        "top_buyer": {"buyer": "Órgano X", "awards": 6},
        "top_cpv_division": {"cpv_division": "72", "awards": 72},
    }
    out = format_market_overview(ov, [{"supplier": "SEIDOR", "wins": 5, "share": 0.079}])
    assert "Inteligencia de mercado" in out
    assert "40.2%" in out
    assert "INETUM" in out
    assert "SEIDOR" in out


def test_format_stats():
    from tender_telegram_bot.bot.messages import format_stats

    out = format_stats({
        "total": 23, "scored_count": 18, "go_count": 4, "avg_score": 71,
        "by_source": {"placsp": 8, "ted": 15},
        "last_ingested_at": "2026-06-26T06:01:00+00:00",
        "last_scored_at": "2026-06-26T06:31:00+00:00",
    })
    assert "Estado del radar" in out
    assert "GO: 4" in out
    assert "placsp: 8" in out


def test_format_expedientes():
    rows = [
        {"tender": {"id": "a", "title": "Plataforma de datos"}, "completeness": 100,
         "days_remaining": 5},
        {"tender": {"id": "b", "title": "Otra licitacion"}, "completeness": 33,
         "days_remaining": 20},
    ]
    out = messages.format_expedientes(rows)
    assert "Expedientes en curso" in out
    assert "100%" in out and "33%" in out
    assert "cierra en 5d" in out
    assert "No hay expedientes" in messages.format_expedientes([])


def test_format_outcomes():
    assert "Aún no hay decisiones" in messages.format_outcomes({"total_decisions": 0})
    s = {"total_decisions": 3, "presented": 3, "won": 2, "lost": 1, "win_rate": 67,
         "won_value": 120000}
    out = messages.format_outcomes(s)
    assert "Win-rate: 67%" in out
    assert "Ganadas: 2" in out and "Perdidas: 1" in out
    assert "120.000" in out


def test_format_pipeline_line():
    exp = [{"tender": {"id": "a"}}, {"tender": {"id": "b"}}]
    line = messages.format_pipeline_line(exp, {"win_rate": 67, "presented": 3})
    assert "2 expediente" in line and "win-rate 67%" in line
    line2 = messages.format_pipeline_line(exp, {"win_rate": None, "presented": 3})
    assert "3 presentada" in line2
