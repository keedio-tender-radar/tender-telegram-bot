"""Handlers de Telegram (capa de integración; la lógica vive en messages/keyboards/jobs)."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from tender_telegram_bot.bot.keyboards import parse_callback
from tender_telegram_bot.clients.tender_api_client import TenderApiClient

_ACTION_FEEDBACK = {
    "interested": "✅ Marcada como interesa",
    "discarded": "❌ Descartada",
    "partner": "🤝 Marcada para partner",
    "prioritize": "📌 Priorizada",
    "review_solvency": "👀 Revisar solvencia",
    "generate_report": "📄 Informe solicitado",
}


def to_markup(buttons: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    """Convierte filas de (label, data) en un teclado inline. data http(s) = botón-enlace."""

    def _btn(label: str, data: str) -> InlineKeyboardButton:
        if data.startswith(("http://", "https://")):
            return InlineKeyboardButton(label, url=data)
        return InlineKeyboardButton(label, callback_data=data)

    return InlineKeyboardMarkup([[_btn(label, data) for label, data in row] for row in buttons])


async def on_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    parsed = parse_callback(query.data)
    if parsed is None:
        await query.answer()
        return
    action, tender_id = parsed
    actor = f"telegram:{query.from_user.id}" if query.from_user else None
    try:
        TenderApiClient().post_action(tender_id, action, actor=actor)
        await query.answer(_ACTION_FEEDBACK.get(action, "Registrado"))
    except Exception:  # noqa: BLE001
        await query.answer("No se pudo registrar la acción", show_alert=True)
