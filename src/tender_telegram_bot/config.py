"""Configuración del bot de Telegram."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "tender-telegram-bot"
    version: str = "0.1.0"

    api_url: str = "http://localhost:8000"

    # Secretos: NUNCA en git. Inyectar por entorno / gestor de secretos.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""  # canal/chat destino del radar diario

    top_limit: int = 5
    urgent_days: int = 7

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
