"""Comandos del bot. Cada comando consulta tender-api y formatea con messages/keyboards."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from tender_telegram_bot.bot import messages
from tender_telegram_bot.bot.handlers import to_markup
from tender_telegram_bot.clients.tender_api_client import TenderApiClient
from tender_telegram_bot.jobs.daily_summary_job import build_daily_summary, build_urgent_alerts

_HELP = (
    "Keedio Tender Radar\n"
    "/resumen — radar diario\n"
    "/top — mejores oportunidades\n"
    "/urgentes — cierres próximos\n"
    "/licitacion <id> — ficha\n"
    "/ayuda — esta ayuda"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_message("Bot de Keedio Tender Radar listo.\n\n" + _HELP)


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_message(_HELP)


async def _send_summary(update: Update) -> None:
    summary = build_daily_summary(TenderApiClient())
    chat = update.effective_chat
    await chat.send_message(summary["header"])
    for item in summary["items"]:
        await chat.send_message(item["text"], reply_markup=to_markup(item["buttons"]))


async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_summary(update)


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_summary(update)


async def cmd_urgentes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    alerts = build_urgent_alerts(TenderApiClient())
    if not alerts:
        await update.effective_chat.send_message("No hay licitaciones urgentes ahora mismo.")
        return
    for alert in alerts:
        await update.effective_chat.send_message(
            alert["text"], reply_markup=to_markup(alert["buttons"])
        )


async def cmd_licitacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_chat.send_message("Uso: /licitacion <id>")
        return
    tender_id = context.args[0]
    api = TenderApiClient()
    try:
        tender = api.get_tender(tender_id)
    except Exception:  # noqa: BLE001
        await update.effective_chat.send_message("No encontré esa licitación.")
        return
    try:
        score = api.get_score(tender_id)
    except Exception:  # noqa: BLE001
        score = None
    await update.effective_chat.send_message(messages.format_tender_detail(tender, score))
