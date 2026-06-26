"""Construye el radar diario a partir de tender-api (cabecera corta + items con botones).

Cabecera CORTA (no repite la lista) + un mensaje por oportunidad con su enlace al panel de
Sites. Función pura sobre el cliente de API: testeable con un doble del cliente, sin Telegram.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tender_telegram_bot.bot import keyboards, messages
from tender_telegram_bot.config import settings

# Estados ya decididos: no deben repetirse en el radar diario (el radar muestra lo accionable).
_DECIDED = {"interested", "discarded", "partner"}


def _is_new(tw: dict, hours: int = 48) -> bool:
    """True si la licitación se ingirió en las últimas `hours` horas."""
    raw = tw.get("tender", {}).get("created_at")
    if not raw:
        return False
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return (datetime.now(UTC) - dt) <= timedelta(hours=hours)


def _item_text(tw: dict, index: int) -> str:
    prefix = "🆕 " if _is_new(tw) else ""
    text = prefix + messages.format_item(tw, index)
    link = messages.ficha_link(settings.dashboard_url, tw.get("tender", {}).get("id", ""))
    return f"{text}\n🔗 {link}" if link else text


def build_daily_summary(api, limit: int | None = None) -> dict:
    """Radar diario: solo oportunidades ACCIONABLES (excluye decididas), marcando las nuevas."""
    limit = limit or settings.top_limit
    candidates = api.get_top(limit * 3)
    actionable = [
        tw for tw in candidates if tw.get("tender", {}).get("status") not in _DECIDED
    ]
    items = actionable[:limit]
    new_count = sum(1 for tw in items if _is_new(tw))
    header = messages.format_digest_header(items, settings.dashboard_url, new_count=new_count)
    item_messages = [
        {
            "tender_id": tw.get("tender", {}).get("id"),
            "text": _item_text(tw, i + 1),
            "buttons": keyboards.item_buttons(tw.get("tender", {}).get("id", "")),
        }
        for i, tw in enumerate(items)
    ]
    return {"header": header, "items": item_messages}


def build_urgent_alerts(api, days: int | None = None) -> list[dict]:
    alerts = []
    for tw in api.get_urgent(days):
        tid = tw.get("tender", {}).get("id", "")
        link = messages.ficha_link(settings.dashboard_url, tid)
        text = messages.format_urgent(tw)
        alerts.append(
            {
                "tender_id": tid,
                "text": f"{text}\n🔗 {link}" if link else text,
                "buttons": keyboards.item_buttons(tid),
            }
        )
    return alerts
