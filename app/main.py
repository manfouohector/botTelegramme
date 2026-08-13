"""Point d'entrée principal de l'application."""

from app.config import get_settings
from app.utils.logging import get_logger, log_event, setup_logging


def main() -> None:
    """Démarre l'application (Module 1 : vérification config uniquement)."""
    settings = get_settings()
    setup_logging(settings)
    logger = get_logger(__name__)

    log_event(
        logger,
        "APP_STARTED",
        app_env=settings.app_env,
        app_name=settings.app_name,
        timezone=settings.timezone,
        has_database=settings.has_database(),
        has_sportmonks=settings.has_sportmonks(),
        has_telegram=settings.has_telegram(),
    )


if __name__ == "__main__":
    main()
