"""Punto de entrada del bot: registra comandos y el handler de acciones, y arranca el polling.

Uso:  python -m tender_telegram_bot.main   (requiere TELEGRAM_BOT_TOKEN).
"""

from __future__ import annotations

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from tender_telegram_bot.bot import commands
from tender_telegram_bot.bot.handlers import on_action
from tender_telegram_bot.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("tender_telegram_bot")


def build_application() -> Application:
    if not settings.telegram_bot_token:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN.")
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", commands.cmd_start))
    app.add_handler(CommandHandler("ayuda", commands.cmd_ayuda))
    app.add_handler(CommandHandler("resumen", commands.cmd_resumen))
    app.add_handler(CommandHandler("top", commands.cmd_top))
    app.add_handler(CommandHandler("urgentes", commands.cmd_urgentes))
    app.add_handler(CommandHandler("licitacion", commands.cmd_licitacion))
    app.add_handler(CallbackQueryHandler(on_action))
    return app


def main() -> None:
    logger.info("Arrancando %s", settings.app_name)
    build_application().run_polling()


if __name__ == "__main__":
    main()
