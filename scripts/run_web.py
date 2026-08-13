#!/usr/bin/env python3
"""Lance le service web FastAPI (health + webhook Telegram) — Render."""

from __future__ import annotations

import os
import sys

import uvicorn

from app.config.settings import get_settings
from app.utils.logging import configure_logging


def main() -> int:
    settings = get_settings()
    configure_logging(settings)
    port = int(os.environ.get("PORT", str(settings.web_port)))
    host = os.environ.get("HOST", "0.0.0.0")

    uvicorn.run(
        "app.api.web_app:app",
        host=host,
        port=port,
        log_level=settings.log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
