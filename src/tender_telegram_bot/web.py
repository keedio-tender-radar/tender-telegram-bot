"""Servicio HTTP del bot (InsForge compute escucha en :8000).

Modo **webhook** (recomendado con scale-to-zero): Telegram hace POST a {public_url}/webhook,
lo que despierta la máquina y entrega los updates. Si no hay `public_url`, cae a *polling*
(que se interrumpe cuando la máquina escala a cero al quedar ociosa).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from telegram import Update

from tender_telegram_bot.config import settings
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
