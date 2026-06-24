FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

COPY pyproject.toml .
RUN pip install --no-cache-dir \
      "pydantic>=2.6" "pydantic-settings>=2.5" "httpx>=0.27" "python-telegram-bot>=21" \
      "tender-contracts @ git+https://github.com/keedio-tender-radar/tender-shared-contracts.git"

COPY . .

# Proceso de larga duración (polling).
CMD ["python", "-m", "tender_telegram_bot.main"]
