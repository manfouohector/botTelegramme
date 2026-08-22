"""FastAPI — health check Render + webhook Telegram (production)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
# pyrefly: ignore [missing-import]
from telegram import Update

from app.bot.application import create_application
from app.config.settings import get_settings
from app.database.session import check_database_connection
from app.utils.logging import get_logger, log_event, setup_logging

logger = get_logger(__name__)

_ptb_application = None
_webhook_path = get_settings().telegram_webhook_path.strip("/") or "telegram"


async def _process_webhook_update(request: Request) -> Response:
    if _ptb_application is None:
        return Response(status_code=503, content="Bot webhook non initialisé")

    payload = await request.json()
    update = Update.de_json(payload, _ptb_application.bot)
    await _ptb_application.process_update(update)
    return Response(status_code=200)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise le bot Telegram en mode webhook si configuré."""
    global _ptb_application
    settings = get_settings()
    setup_logging(settings)

    if settings.has_telegram() and settings.telegram_bot_mode == "webhook":
        _ptb_application = create_application(settings)
        await _ptb_application.initialize()
        await _ptb_application.start()

        webhook_url = settings.telegram_webhook_url.strip()
        if webhook_url:
            await _ptb_application.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=settings.telegram_drop_pending_updates,
            )
            log_event(logger, "WEBHOOK_REGISTERED", url=webhook_url)

    log_event(
        logger,
        "WEB_APP_STARTED",
        app_env=settings.app_env,
        bot_mode=settings.telegram_bot_mode,
        webhook_path=f"/{_webhook_path}",
        has_database=settings.has_database(),
    )
    yield

    if _ptb_application is not None:
        await _ptb_application.stop()
        await _ptb_application.shutdown()
        _ptb_application = None


app = FastAPI(
    title="Football Prediction Bot",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_api_route(f"/{_webhook_path}", _process_webhook_update, methods=["POST"])


@app.get("/health")
async def health() -> dict:
    """Health check Render — doit retourner HTTP 200."""
    settings = get_settings()
    db_ok = check_database_connection(settings) if settings.has_database() else False
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "database_ok": db_ok,
        "telegram_configured": settings.has_telegram(),
        "bot_mode": settings.telegram_bot_mode,
    }


@app.get("/")
async def root() -> dict:
    return {"service": "football-prediction-bot", "health": "/health"}
