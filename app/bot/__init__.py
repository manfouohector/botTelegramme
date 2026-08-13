"""Bot Telegram — infrastructure de base."""

__all__ = [
    "create_application",
    "run_bot",
    "BotContext",
    "BotError",
    "BotNotConfiguredError",
]


def __getattr__(name: str):
    if name == "create_application":
        from app.bot.application import create_application
        return create_application
    if name == "run_bot":
        from app.bot.runner import run_bot
        return run_bot
    if name == "BotContext":
        from app.bot.context import BotContext
        return BotContext
    if name == "BotError":
        from app.bot.exceptions import BotError
        return BotError
    if name == "BotNotConfiguredError":
        from app.bot.exceptions import BotNotConfiguredError
        return BotNotConfiguredError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
