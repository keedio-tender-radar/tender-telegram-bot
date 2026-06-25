FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app/vendor

# tender-contracts vendorizado en ./vendor (repo privado). Generar antes del deploy:
#   bash scripts/vendor-contracts.sh
COPY pyproject.toml .
RUN pip install --no-cache-dir \
      "pydantic>=2.6" "pydantic-settings>=2.5" "httpx>=0.27" "python-telegram-bot>=21" \
      "fastapi>=0.115" "uvicorn[standard]>=0.32"

COPY . .

EXPOSE 8000

# Servicio: sirve /health en :8000 y arranca el polling de Telegram en el lifespan.
# (El polling puro sigue disponible vía `python -m tender_telegram_bot.main`.)
CMD ["uvicorn", "tender_telegram_bot.web:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
