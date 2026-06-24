# tender-telegram-bot

> 🤖 Bot de Telegram de **Keedio Tender Radar**: radar diario, alertas urgentes y acciones con
> botones inline. Consume `tender-api`.

## Qué hace

- **Radar diario** (`/resumen`, `/top`): cabecera + las mejores oportunidades (`/api/tenders/top`),
  cada una con botones de acción.
- **Urgentes** (`/urgentes`): cierres próximos (`/api/tenders/urgent`).
- **Ficha** (`/licitacion <id>`): detalle + score + factores.
- **Acciones**: los botones registran la decisión en `tender-api`
  (`POST /api/tenders/{id}/actions`): interesa, descartar, partner, prioritaria, revisar solvencia,
  informe.

## Diseño (testable sin Telegram)

La lógica vive en módulos **puros** (sin `python-telegram-bot`):

| Módulo | Responsabilidad |
|--------|-----------------|
| `bot/messages.py` | Formato de mensajes (radar, urgente, ficha) |
| `bot/keyboards.py` | Botones inline como datos + `callback_data`/`parse_callback` |
| `jobs/daily_summary_job.py` | Construye radar y alertas desde la API |
| `clients/tender_api_client.py` | Cliente HTTP a tender-api |

Telegram solo aparece en `bot/handlers.py`, `bot/commands.py` y `main.py`.

## Ejecutar

```bash
python -m venv .venv && . .venv/Scripts/activate    # Linux/mac: source .venv/bin/activate
pip install -e ../tender-shared-contracts
pip install pydantic pydantic-settings httpx "python-telegram-bot>=21" pytest ruff

export TELEGRAM_BOT_TOKEN=...      # secreto, nunca en git
export API_URL=http://localhost:8000
python -m tender_telegram_bot.main   # arranca el polling

pytest -q          # 17 tests (mensajes + teclados + jobs + cliente), sin Telegram ni red
ruff check src tests
```

## Comandos

```
/start · /ayuda · /resumen · /top · /urgentes · /licitacion <id>
```

## Notas

- `callback_data` = `action:<action>:<tender_id>`; `parse_callback` usa `maxsplit=2` para no romper
  los UUID con guiones.
- El **token de Telegram es un secreto**: inyectar por entorno / gestor de secretos, nunca en git.
- El envío programado del radar diario se hace por cron/scheduler (infra) invocando el bot.
