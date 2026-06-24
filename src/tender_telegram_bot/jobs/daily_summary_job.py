"""Construye el radar diario a partir de tender-api (cabecera + items con botones).

Función pura sobre el cliente de API: testeable con un doble del cliente, sin Telegram.
"""

from __future__ import annotations

from tender_telegram_bot.bot import keyboards, messages


def build_daily_summary(api, limit: int | None = None) -> dict:
    items = api.get_top(limit)
    header = messages.format_daily_digest(items)
    item_messages = [
        {
            "tender_id": tw.get("tender", {}).get("id"),
            "text": messages.format_item(tw, i + 1),
            "buttons": keyboards.item_buttons(tw.get("tender", {}).get("id", "")),
        }
        for i, tw in enumerate(items)
    ]
    return {"header": header, "items": item_messages}


def build_urgent_alerts(api, days: int | None = None) -> list[dict]:
    alerts = []
    for tw in api.get_urgent(days):
        tid = tw.get("tender", {}).get("id", "")
        alerts.append(
            {
                "tender_id": tid,
                "text": messages.format_urgent(tw),
                "buttons": keyboards.item_buttons(tid),
            }
        )
    return alerts
