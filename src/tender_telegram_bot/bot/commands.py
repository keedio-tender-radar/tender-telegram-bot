"""Comandos del bot. Cada comando consulta tender-api y formatea con messages/keyboards.

Todos los comandos son robustos: si algo falla, responden con un mensaje claro en vez de quedar
en silencio (un handler que lanza sin responder deja al usuario sin feedback).
"""

from __future__ import annotations

import functools
import logging

from telegram import Update
from telegram.ext import ContextTypes

from tender_telegram_bot.bot import messages
from tender_telegram_bot.bot.handlers import to_markup
from tender_telegram_bot.clients.tender_api_client import TenderApiClient
from tender_telegram_bot.config import settings
from tender_telegram_bot.jobs.daily_summary_job import build_daily_summary, build_urgent_alerts

logger = logging.getLogger("tender_telegram_bot")

_HELP = (
    "Keedio Tender Radar\n"
    "/resumen — radar diario\n"
    "/top — mejores oportunidades\n"
    "/urgentes — cierres próximos\n"
    "/licitacion <id> — ficha\n"
    "/preguntar <id> <pregunta> — pregunta al pliego\n"
    "/mercado [id] — inteligencia de mercado (global, o de un expediente)\n"
    "/competidor <nombre> — perfil de un adjudicatario\n"
    "/buscar <palabras> — busca licitaciones\n"
    "/expedientes — expedientes en curso y su progreso\n"
    "/resultados — win-rate del pipeline (presentadas/ganadas/perdidas)\n"
    "/estado — estado del radar\n"
    "/ayuda — esta ayuda"
)


def safe(handler):
    """Captura errores del comando y responde con un mensaje (evita fallos en silencio)."""

    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            await handler(update, context)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error en %s", handler.__name__)
            if update.effective_chat:
                await update.effective_chat.send_message(f"⚠️ No se pudo completar: {exc}")

    return wrapper


@safe
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    await chat.send_message(
        "Bot de Keedio Tender Radar listo.\n\n"
        + _HELP
        + f"\n\n(Para el radar diario automático, este chat_id es: {chat.id})"
    )


@safe
async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_message(_HELP)


async def _send_summary(update: Update) -> None:
    summary = build_daily_summary(TenderApiClient())
    chat = update.effective_chat
    await chat.send_message(summary["header"], disable_web_page_preview=True)
    for item in summary["items"]:
        await chat.send_message(
            item["text"], reply_markup=to_markup(item["buttons"]), disable_web_page_preview=True
        )


@safe
async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_summary(update)


@safe
async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_summary(update)


@safe
async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = TenderApiClient()
    msg = messages.format_stats(api.get_stats())
    try:  # línea de pipeline: no debe tumbar el estado si un endpoint falla
        msg += "\n\n" + messages.format_pipeline_line(
            api.get_expedientes(), api.get_outcomes_summary()
        )
    except Exception:  # noqa: BLE001
        logger.warning("No se pudo añadir la línea de pipeline a /estado")
    await update.effective_chat.send_message(msg)


@safe
async def cmd_expedientes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = TenderApiClient().get_expedientes()
    await update.effective_chat.send_message(
        messages.format_expedientes(rows), disable_web_page_preview=True
    )


@safe
async def cmd_resultados(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    summary = TenderApiClient().get_outcomes_summary()
    await update.effective_chat.send_message(messages.format_outcomes(summary))


@safe
async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_chat.send_message("Uso: /buscar <palabras>")
        return
    q = " ".join(context.args)
    results = TenderApiClient().search(q)
    if not results:
        await update.effective_chat.send_message(f"Sin resultados para «{q}».")
        return
    chat = update.effective_chat
    await chat.send_message(f'🔎 Resultados para «{q}»:')
    for i, tw in enumerate(results):
        await chat.send_message(
            messages.format_item(tw, i + 1)
            + (f"\n🔗 {messages.ficha_link(settings.dashboard_url, tw['tender']['id'])}"),
            disable_web_page_preview=True,
        )


@safe
async def cmd_urgentes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    alerts = build_urgent_alerts(TenderApiClient())
    if not alerts:
        await update.effective_chat.send_message("No hay licitaciones urgentes ahora mismo.")
        return
    for alert in alerts:
        await update.effective_chat.send_message(
            alert["text"], reply_markup=to_markup(alert["buttons"]), disable_web_page_preview=True
        )


@safe
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
    text = messages.format_tender_detail(tender, score)
    link = messages.ficha_link(settings.dashboard_url, tender_id)
    if link:
        text += f"\n🔗 {link}"
    await update.effective_chat.send_message(text, disable_web_page_preview=True)


@safe
async def cmd_mercado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api = TenderApiClient()
    # Sin id → resumen global de mercado; con id → contexto competitivo del expediente.
    if not context.args:
        ov = api.market_overview()
        competitors = api.market_competitors(5)
        await update.effective_chat.send_message(
            messages.format_market_overview(ov, competitors), disable_web_page_preview=True
        )
        return
    tender_id = context.args[0]
    try:
        tender = api.get_tender(tender_id)
    except Exception:  # noqa: BLE001
        await update.effective_chat.send_message("No encontré esa licitación.")
        return
    ctx = api.market_context(tender_id)
    await update.effective_chat.send_message(
        messages.format_market_context(tender, ctx), disable_web_page_preview=True
    )


@safe
async def cmd_competidor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_chat.send_message("Uso: /competidor <nombre de la empresa>")
        return
    name = " ".join(context.args)
    prof = TenderApiClient().competitor_profile(name)
    if not prof:
        await update.effective_chat.send_message(f"Sin adjudicaciones para «{name}».")
        return
    await update.effective_chat.send_message(
        messages.format_competitor_profile(prof), disable_web_page_preview=True
    )


@safe
async def cmd_preguntar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.effective_chat.send_message("Uso: /preguntar <id> <pregunta>")
        return
    tender_id = context.args[0]
    question = " ".join(context.args[1:])
    await update.effective_chat.send_message("🔎 Consultando el pliego…")
    result = TenderApiClient().ask(tender_id, question)
    text = messages.format_answer(question, result)
    link = messages.ficha_link(settings.dashboard_url, tender_id)
    if link:
        text += f"\n🔗 {link}"
    await update.effective_chat.send_message(text, disable_web_page_preview=True)
