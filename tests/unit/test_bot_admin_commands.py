"""Tests unitaires — commandes admin /generate, /status, /history."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import sessionmaker
from telegram import Chat, Message, Update, User

from app.bot.context import BotContext
from app.bot.handlers.admin import generate_command, history_command, status_command
from app.config.settings import Settings
from app.database.enums import SystemRunStatus
from app.generation.schemas import GenerationBatchResult
from tests.fixtures.generation_helpers import seed_history_day, seed_status_day


@pytest.fixture
def admin_settings():
    return Settings(_env_file=None, admin_telegram_id="900001", timezone="UTC")


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, autocommit=False, autoflush=False)


@pytest.fixture
def admin_context(admin_settings, session_factory):
    return BotContext(settings=admin_settings, session_factory=session_factory)


def _admin_update(admin_id: int = 900001, args: list[str] | None = None):
    user = User(id=admin_id, is_bot=False, first_name="Admin")
    chat = Chat(id=admin_id, type="private")
    message = MagicMock(spec=Message)
    message.chat = chat
    message.reply_text = AsyncMock()
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_message = message
    context = MagicMock()
    context.args = args or []
    return update, context


class TestAdminGenerateCommand:
    async def test_denied_for_non_admin(self, admin_context):
        update, context = _admin_update(admin_id=111)
        context.application = MagicMock()
        context.application.bot_data = {"ctx": admin_context}
        await generate_command(update, context)
        assert update.effective_message.reply_text.await_count == 1
        assert "refusé" in update.effective_message.reply_text.await_args_list[0].args[0].lower()

    async def test_generate_success_message(self, admin_context):
        update, context = _admin_update()
        context.application = MagicMock()
        context.application.bot_data = {"ctx": admin_context}

        fake_result = GenerationBatchResult(
            target_date=datetime(2026, 8, 12, tzinfo=timezone.utc).date(),
            matches_analyzed=5,
            predictions_created=10,
            coupons_created=2,
            status=SystemRunStatus.SUCCESS,
        )

        with patch(
            "app.bot.handlers.admin.GenerationService.run",
            return_value=fake_result,
        ):
            await generate_command(update, context)

        assert update.effective_message.reply_text.await_count == 2
        final_text = update.effective_message.reply_text.await_args_list[1].args[0]
        assert "Génération terminée" in final_text
        assert "Coupons créés : 2" in final_text


class TestAdminStatusCommand:
    async def test_denied_for_non_admin(self, admin_context):
        update, context = _admin_update(admin_id=111)
        context.application = MagicMock()
        context.application.bot_data = {"ctx": admin_context}
        await status_command(update, context)
        assert "refusé" in update.effective_message.reply_text.await_args.args[0].lower()

    async def test_status_replies_with_daily_data(self, admin_context, monkeypatch):
        session = admin_context.session_factory()
        day = datetime(2026, 8, 12, 8, 0, tzinfo=timezone.utc)
        seeded = seed_status_day(session, day=day)
        session.commit()
        session.close()

        monkeypatch.setattr(
            "app.services.status_service.StatusService._today",
            lambda self: seeded["day"],
        )

        update, context = _admin_update()
        context.application = MagicMock()
        context.application.bot_data = {"ctx": admin_context}
        await status_command(update, context)

        text = update.effective_message.reply_text.await_args.args[0]
        assert "STATUT DU 12/08/2026" in text
        assert "FREE" in text


class TestAdminHistoryCommand:
    async def test_invalid_date_usage(self, admin_context):
        update, context = _admin_update(args=["bad-date"])
        context.application = MagicMock()
        context.application.bot_data = {"ctx": admin_context}
        await history_command(update, context)
        assert "Usage" in update.effective_message.reply_text.await_args.args[0]

    async def test_history_summary(self, admin_context):
        session = admin_context.session_factory()
        day = datetime(2026, 8, 11, 18, 0, tzinfo=timezone.utc)
        seed_history_day(session, day=day)
        session.commit()
        session.close()

        update, context = _admin_update(args=["2026-08-11"])
        context.application = MagicMock()
        context.application.bot_data = {"ctx": admin_context}
        await history_command(update, context)

        text = update.effective_message.reply_text.await_args.args[0]
        assert "HISTORIQUE — 11/08/2026" in text
        assert "13" in text
        assert "3" in text
