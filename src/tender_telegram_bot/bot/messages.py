"""Formato de los mensajes del bot (funciones puras, sin dependencia de Telegram).

Ver tender-platform-docs/telegram-notification-format.md.
"""

from __future__ import annotations

_REC_LABEL = {
    "go": "GO",
    "revisar": "REVISAR",
    "partner": "PARTNER",
    "no_go": "NO-GO",
}


def _money(amount, currency: str = "EUR") -> str:
    if amount is None:
        return "s/d"
    return f"{amount:,.0f} {currency}".replace(",", ".")


def _date(value) -> str:
    if not value:
        return "s/d"
    return str(value)[:10]


def _rec(score: dict | None) -> str:
    if not score:
        return "sin score"
    return _REC_LABEL.get(score.get("recommendation", ""), score.get("recommendation", "?"))


def format_item(tw: dict, index: int | None = None) -> str:
    """Bloque de una oportunidad (para el radar diario)."""
    t = tw.get("tender", {})
    s = tw.get("score")
    prefix = f"{index}. " if index is not None else ""
    score_txt = f"{s['total']}/100 · {_rec(s)}" if s else _rec(s)
    lines = [
        f"{prefix}{t.get('title', '(sin título)')}",
        f"   Score: {score_txt}",
        f"   Presupuesto: {_money(t.get('budget_amount'), t.get('currency', 'EUR'))}"
        f" · Plazo: {_date(t.get('deadline'))}",
    ]
    if t.get("buyer"):
        lines.append(f"   Órgano: {t['buyer']}")
    return "\n".join(lines)


def format_daily_digest(items: list[dict], stats: dict | None = None) -> str:
    head = ["📊 Keedio Tender Radar — Resumen diario", ""]
    if stats:
        head.append(
            f"Analizadas: {stats.get('analyzed', '?')} · "
            f"Relevantes: {stats.get('relevant', '?')} · "
            f"Prioritarias: {stats.get('prioritized', '?')} · "
            f"Descartadas: {stats.get('discarded', '?')}"
        )
        head.append("")
    if not items:
        head.append("Hoy no hay oportunidades destacadas.")
        return "\n".join(head)
    head.append("TOP oportunidades")
    head.append("")
    blocks = [format_item(tw, i + 1) for i, tw in enumerate(items)]
    return "\n".join(head) + "\n" + "\n\n".join(blocks)


def format_digest_header(
    items: list[dict], dashboard_url: str | None = None, new_count: int = 0
) -> str:
    """Cabecera CORTA del radar (sin repetir la lista; el detalle va en los items y el panel)."""
    n = len(items)
    if n == 0:
        msg = "📊 Keedio Tender Radar — hoy no hay oportunidades accionables nuevas."
    else:
        nuevas = f" · 🆕 {new_count} nueva(s)" if new_count else ""
        msg = f"📊 Keedio Tender Radar — {n} oportunidad(es) por revisar{nuevas}:"
    if dashboard_url:
        msg += f"\n🔗 Panel: {dashboard_url}"
    return msg


def ficha_link(dashboard_url: str | None, tender_id: str) -> str:
    return f"{dashboard_url.rstrip('/')}/tenders/{tender_id}" if dashboard_url else ""


def format_answer(question: str, result: dict) -> str:
    """Formatea la respuesta de /ask (visual-rag o extractivo) para Telegram."""
    answer = result.get("answer") or "No encontré una respuesta en el pliego."
    n = len(result.get("sources") or [])
    footer = f"motor: {result.get('backend', '?')} · {n} fuente(s)"
    return "\n".join([f"❓ {question}", "", answer, "", footer])


def format_alert(tw: dict) -> str:
    """Alerta de oportunidad prioritaria (GO recién detectada)."""
    t = tw.get("tender", {})
    s = tw.get("score")
    score_txt = f"{s['total']}/100" if s else "?"
    return (
        "🟢 Nueva oportunidad prioritaria (GO)\n\n"
        f"{t.get('title', '(sin título)')}\n"
        f"Score: {score_txt} · Fuente: {t.get('source', '?')}\n"
        f"Presupuesto: {_money(t.get('budget_amount'), t.get('currency', 'EUR'))}"
        f" · Plazo: {_date(t.get('deadline'))}"
    )


def format_urgent(tw: dict) -> str:
    t = tw.get("tender", {})
    s = tw.get("score")
    score_txt = f"Score {s['total']}/100 ({_rec(s)})" if s else _rec(s)
    return (
        "🚨 Licitación urgente\n\n"
        f"{t.get('title', '(sin título)')} — {score_txt}\n"
        f"⏳ Cierre: {_date(t.get('deadline'))}\n"
        f"Presupuesto: {_money(t.get('budget_amount'), t.get('currency', 'EUR'))}"
    )


def format_tender_detail(tender: dict, score: dict | None = None) -> str:
    lines = [
        tender.get("title", "(sin título)"),
        "",
        f"Dominio/fuente: {tender.get('source', '?')}",
        f"Presupuesto: {_money(tender.get('budget_amount'), tender.get('currency', 'EUR'))}",
        f"Plazo: {_date(tender.get('deadline'))}",
        f"Estado: {tender.get('status', '?')}",
    ]
    if tender.get("cpv"):
        lines.append(f"CPV: {', '.join(tender['cpv'])}")
    if score:
        lines += ["", f"Score: {score['total']}/100 · {_rec(score)}"]
        for f in score.get("factors", [])[:6]:
            mark = "➕" if f.get("kind") == "positive" else "➖"
            lines.append(f"{mark} {f.get('message', '')}")
    if tender.get("url"):
        lines += ["", tender["url"]]
    return "\n".join(lines)
