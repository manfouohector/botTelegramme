#!/usr/bin/env python
"""Lance le bot Telegram en mode polling ou webhook."""

from __future__ import annotations

import sys

from app.bot.exceptions import BotError
from app.bot.runner import run_bot
from app.database.session import reset_engine


def main() -> int:
    try:
        run_bot()
        return 0
    except BotError as exc:
        print(f"Erreur bot : {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Arrêt du bot.")
        return 0
    finally:
        reset_engine()


if __name__ == "__main__":
    sys.exit(main())
