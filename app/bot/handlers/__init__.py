"""Enregistrement des handlers bot."""

from __future__ import annotations

from telegram import Update
from telegram.ext import Application, TypeHandler

from app.bot.handlers import admin, callbacks, commands, errors, fallback, health
from app.bot.middleware import user_tracking_middleware


def register_handlers(application: Application) -> None:
    """Enregistre tous les handlers du bot."""
    application.add_handler(TypeHandler(Update, user_tracking_middleware), group=-1)
    errors.register_error_handler(application)
    health.register_health_handlers(application)
    commands.register_command_handlers(application)
    admin.register_admin_handlers(application)
    callbacks.register_callback_handlers(application)
    fallback.register_fallback_handlers(application)
