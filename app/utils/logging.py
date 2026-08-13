"""Configuration du logging structuré."""

import logging
import sys
from typing import Literal

from app.config.settings import Settings, get_settings

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(settings: Settings | None = None) -> None:
    """Configure le logging global une seule fois."""
    global _configured
    if _configured:
        return

    cfg = settings or get_settings()
    level = getattr(logging, cfg.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Évite les handlers dupliqués en cas de reconfiguration
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        root.addHandler(handler)

    # Réduit le bruit des librairies tierces en production
    if cfg.is_production:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger nommé, après initialisation si nécessaire."""
    setup_logging()
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    event: str,
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
    **kwargs: object,
) -> None:
    """Log un événement structuré sous forme clé=valeur."""
    parts = [f"{key}={value}" for key, value in kwargs.items()]
    message = f"{event}" + (f" | {' | '.join(parts)}" if parts else "")
    getattr(logger, level.lower())(message)
