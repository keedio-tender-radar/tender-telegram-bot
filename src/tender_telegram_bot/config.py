"""Configuración del bot de Telegram."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "tender-telegram-bot"
    version: str = "0.1.0"

    api_url: str = "http://localhost:8000"

    # Secretos: NUNCA en git. Inyectar por entorno / gestor de secretos.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""  # destino(s) del radar; admite varios separados por coma

    @property
    def telegram_chat_ids(self) -> list[str]:
        """Lista de chats destino (multi-destinatario): TELEGRAM_CHAT_ID coma-separado."""
        return [c.strip() for c in self.telegram_chat_id.split(",") if c.strip()]

    top_limit: int = 5
    urgent_days: int = 7

    # Dashboard de Sites (InsForge): el bot enlaza aquí para el detalle visual.
    dashboard_url: str = "https://vz4wf92x.insforge.site"

    # Webhook (recomendado con scale-to-zero). Si public_url está definido, el bot usa webhook
    # en {public_url}/webhook; si no, cae a polling (se duerme si la máquina escala a cero).
    public_url: str = ""
    webhook_secret: str = ""

    # Token que protege el envío programado del radar (POST /send-digest desde el scheduler).
    run_token: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
