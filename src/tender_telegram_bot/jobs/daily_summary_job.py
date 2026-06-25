"""Construye el radar diario a partir de tender-api (cabecera corta + items con botones).

Cabecera CORTA (no repite la lista) + un mensaje por oportunidad con su enlace al panel de
Sites. Función pura sobre el cliente de API: testeable con un doble del cliente, sin Telegram.
"""

from __future__ import annotations

from tender_telegram_bot.bot import keyboards, messages
from tender_telegram_bot.config import settings


def _item_text(tw: dict, index: int) -> str:
    text = messages.format_item(tw, index)
    link = messages.ficha_link(settings.dashboard_url, tw.get("tender", {}).get("id", ""))
    return f"{text}\n🔗 {link}" if link else text


def build_daily_summary(api, limit: int | None = None) -> dict:
    items = api.get_top(limit)
    header = messages.format_digest_header(items, settings.dashboard_url)
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
