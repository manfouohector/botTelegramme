"""Tests unitaires — logging."""

import logging

from app.config.settings import Settings
from app.utils.logging import get_logger, log_event, setup_logging


class TestLogging:
    """Vérifie la configuration du logging."""

    def setup_method(self):
        # Reset logging state between tests
        import app.utils.logging as logging_module

        logging_module._configured = False
        root = logging.getLogger()
        root.handlers.clear()

    def test_setup_logging_creates_handler(self):
        setup_logging(Settings(log_level="DEBUG"))
        root = logging.getLogger()
        assert len(root.handlers) >= 1
        assert root.level == logging.DEBUG

    def test_setup_logging_idempotent(self):
        setup_logging(Settings())
        handler_count_after_first = len(logging.getLogger().handlers)
        setup_logging(Settings())
        assert len(logging.getLogger().handlers) == handler_count_after_first

    def test_get_logger_returns_named_logger(self):
        logger = get_logger("test.module")
        assert logger.name == "test.module"

    def test_log_event_formats_message(self, caplog):
        setup_logging(Settings(log_level="INFO"))
        logger = get_logger("test")
        with caplog.at_level(logging.INFO):
            log_event(logger, "DATA_COLLECTION_STARTED", match_count=18)
        assert "DATA_COLLECTION_STARTED" in caplog.text
        assert "match_count=18" in caplog.text
