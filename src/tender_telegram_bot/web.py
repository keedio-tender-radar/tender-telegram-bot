"""Servicio HTTP del bot (InsForge compute escucha en :8000).

Modo **webhook** (recomendado con scale-to-zero): Telegram hace POST a {public_url}/webhook,
lo que despierta la máquina y entrega los updates. Si no hay `public_url`, cae a *polling*
(que se interrumpe cuando la máquina escala a cero al quedar ociosa).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from telegram import Update

from tender_telegram_bot.bot import keyboards, messages
from tender_telegram_bot.bot.handlers import to_markup
from tender_telegram_bot.clients.tender_api_client import TenderApiClient
from tender_telegram_bot.config import settings
from tender_telegram_bot.jobs.daily_summary_job import build_daily_summary
from tender_telegram_bot.main import build_application

logger = logging.getLogger("tender_telegram_bot")

_application = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _application
    if settings.telegram_bot_token:
        _application = build_application()
        await _application.initialize()
        await _application.start()
        if settings.public_url:
            url = settings.public_url.rstrip("/") + "/webhook"
            await _application.bot.set_webhook(
                url=url,
                allowed_updates=Update.ALL_TYPES,
                secret_token=settings.webhook_secret or None,
            )
            logger.info("Webhook configurado en %s", url)
        else:
            await _application.updater.start_polling(drop_pending_updates=True)
            logger.warning("Sin PUBLIC_URL → polling (se duerme con scale-to-zero).")
    else:
        logger.warning("Sin TELEGRAM_BOT_TOKEN: solo /health.")
    try:
        yield
    finally:
        if _application:
            if not settings.public_url:
                await _application.updater.stop()
            await _application.stop()
            await _application.shutdown()


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    if settings.public_url:
        mode = "webhook"
    elif settings.telegram_bot_token:
        mode = "polling"
    else:
        mode = "off"
    return {"status": "ok", "service": settings.app_name, "version": settings.version, "mode": mode}


@app.post("/send-digest")
async def send_digest(x_run_token: str | None = Header(default=None)) -> dict:
    """Envía el radar diario al chat configurado (TELEGRAM_CHAT_ID). Para el scheduler."""
    if settings.run_token and x_run_token != settings.run_token:
        raise HTTPException(401, "Token de ejecución inválido o ausente.")
    if not settings.telegram_chat_id:
        raise HTTPException(400, "Falta TELEGRAM_CHAT_ID (destino del radar).")
    if _application is None:
        raise HTTPException(503, "Bot no inicializado.")
    summary = build_daily_summary(TenderApiClient())
    chat = settings.telegram_chat_id
    bot = _application.bot
    await bot.send_message(chat, summary["header"], disable_web_page_preview=True)
    for item in summary["items"]:
        await bot.send_message(
            chat, item["text"], reply_markup=to_markup(item["buttons"]),
            disable_web_page_preview=True,
        )
    return {"sent": len(summary["items"]) + 1, "chat_id": chat}


@app.post("/send-alerts")
async def send_alerts(x_run_token: str | None = Header(default=None)) -> dict:
    """Envía alertas inmediatas de oportunidades GO no alertadas y las marca como alertadas."""
    if settings.run_token and x_run_token != settings.run_token:
        raise HTTPException(401, "Token de ejecución inválido o ausente.")
    if not settings.telegram_chat_id:
        raise HTTPException(400, "Falta TELEGRAM_CHAT_ID (destino de las alertas).")
    if _application is None:
        raise HTTPException(503, "Bot no inicializado.")
    api = TenderApiClient()
    pending = api.get_pending_alerts()
    chat = settings.telegram_chat_id
    sent = 0
    for tw in pending:
        tid = tw.get("tender", {}).get("id", "")
        await _application.bot.send_message(
            chat, messages.format_alert(tw),
            reply_markup=to_markup(keyboards.item_buttons(tid)),
            disable_web_page_preview=True,
        )
        try:
            api.mark_alerted(tid)
        except Exception:  # noqa: BLE001 — no re-alertar es preferible a fallar
            pass
        sent += 1
    return {"sent": sent}


@app.post("/webhook")
async def webhook(request: Request) -> dict:
    if settings.webhook_secret:
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != settings.webhook_secret:
            return {"ok": False}
    if _application is None:
        return {"ok": False}
    data = await request.json()
    await _application.process_update(Update.de_json(data, _application.bot))
    return {"ok": True}
