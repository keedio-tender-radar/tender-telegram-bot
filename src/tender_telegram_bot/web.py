"""Envoltura HTTP para desplegar el bot como servicio (InsForge compute escucha en :8000).

Sirve `/health` y arranca el polling de Telegram en el lifespan de FastAPI, así el contenedor
escucha en el puerto y a la vez procesa comandos/acciones. Sin TELEGRAM_BOT_TOKEN, solo /health.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from tender_telegram_bot.config import settings
from tender_telegram_bot.main import build_application

logger = logging.getLogger("tender_telegram_bot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    application = None
    if settings.telegram_bot_token:
        application = build_application()
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        logger.info("Polling de Telegram iniciado")
    else:
        logger.warning("Sin TELEGRAM_BOT_TOKEN: el bot no hace polling (solo /health).")
    try:
        yield
    finally:
        if application:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
        "polling": bool(settings.telegram_bot_token),
    }
