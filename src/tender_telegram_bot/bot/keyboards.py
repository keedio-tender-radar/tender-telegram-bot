"""Teclados inline como datos puros (sin dependencia de Telegram).

Cada botón es `(label, callback_data)`. El callback_data codifica `action:<action>:<tender_id>`.
handlers.py los convierte a InlineKeyboardMarkup y los parsea de vuelta.
"""

from __future__ import annotations

ACTION_PREFIX = "action"

# (etiqueta, acción) — la acción debe ser un ActionType válido de tender-contracts.
_BUTTONS = [
    ("✅ Interesa", "interested"),
    ("❌ Descartar", "discarded"),
    ("🤝 Partner", "partner"),
    ("📌 Prioritaria", "prioritize"),
    ("👀 Revisar solvencia", "review_solvency"),
    ("📄 Informe", "generate_report"),
]


def callback_data(action: str, tender_id: str) -> str:
    return f"{ACTION_PREFIX}:{action}:{tender_id}"


def parse_callback(data: str) -> tuple[str, str] | None:
    """Devuelve (action, tender_id) si el callback es de acción, si no None."""
    parts = (data or "").split(":", 2)
    if len(parts) != 3 or parts[0] != ACTION_PREFIX:
        return None
    _, action, tender_id = parts
    if not action or not tender_id:
        return None
    return action, tender_id


def item_buttons(tender_id: str, dashboard_url: str = "") -> list[list[tuple[str, str]]]:
    """Filas de botones (etiqueta, callback_data) para una oportunidad. 2 por fila.

    Si hay `dashboard_url`, añade un botón-enlace «📄 Ficha» a la web (callback_data = URL http).
    """
    flat = [(label, callback_data(action, tender_id)) for label, action in _BUTTONS]
    rows = [flat[i : i + 2] for i in range(0, len(flat), 2)]
    if dashboard_url:
        rows.append([("📄 Ficha", f"{dashboard_url.rstrip('/')}/tenders/{tender_id}")])
    return rows
