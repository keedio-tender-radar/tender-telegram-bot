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


def _report_run(job: str, status: str, count: int | None = None, detail: str | None = None) -> None:
    """Reporta el resultado del envío a tender-api (/api/runs) para observabilidad. Best-effort."""
    if not settings.api_url:
        return
    try:
        import httpx

        headers = {"X-Run-Token": settings.run_token} if settings.run_token else {}
        httpx.post(
            f"{settings.api_url.rstrip('/')}/api/runs",
            json={"job": job, "status": status, "count": count, "detail": detail},
            headers=headers,
            timeout=10,
        )
    except Exception:  # noqa: BLE001
        pass


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
    bot = _application.bot
    chats = settings.telegram_chat_ids
    for chat in chats:
        await bot.send_message(chat, summary["header"], disable_web_page_preview=True)
        for item in summary["items"]:
            await bot.send_message(
                chat, item["text"], reply_markup=to_markup(item["buttons"]),
                disable_web_page_preview=True,
            )
    _report_run("digest", "ok", count=len(summary["items"]))
    return {"sent": (len(summary["items"]) + 1) * len(chats), "chats": len(chats)}


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
    chats = settings.telegram_chat_ids
    sent = 0
    for tw in pending:
        tid = tw.get("tender", {}).get("id", "")
        for chat in chats:
            await _application.bot.send_message(
                chat, messages.format_alert(tw),
                reply_markup=to_markup(keyboards.item_buttons(tid, settings.dashboard_url)),
                disable_web_page_preview=True,
            )
        try:
            api.mark_alerted(tid)
        except Exception:  # noqa: BLE001 — no re-alertar es preferible a fallar
            pass
        sent += 1
    _report_run("alertas", "ok", count=sent)
    return {"sent": sent, "chats": len(chats)}


@app.post("/send-reminders")
async def send_reminders(x_run_token: str | None = Header(default=None)) -> dict:
    """Recuerda los cierres próximos de licitaciones en seguimiento (interested/partner)."""
    if settings.run_token and x_run_token != settings.run_token:
        raise HTTPException(401, "Token de ejecución inválido o ausente.")
    if not settings.telegram_chat_id:
        raise HTTPException(400, "Falta TELEGRAM_CHAT_ID.")
    if _application is None:
        raise HTTPException(503, "Bot no inicializado.")
    api = TenderApiClient()
    chats = settings.telegram_chat_ids
    sent = 0
    for tw in api.get_closing_soon():
        tid = tw.get("tender", {}).get("id", "")
        text = "⏰ Cierre próximo (en seguimiento)\n\n" + messages.format_urgent(tw)
        link = messages.ficha_link(settings.dashboard_url, tid)
        for chat in chats:
            await _application.bot.send_message(
                chat, f"{text}\n🔗 {link}" if link else text, disable_web_page_preview=True
            )
        try:
            api.mark_reminded(tid)
        except Exception:  # noqa: BLE001
            pass
        sent += 1
    _report_run("recordatorios", "ok", count=sent)
    return {"sent": sent, "chats": len(chats)}


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
