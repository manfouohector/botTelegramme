"""Tests d'intégration — point d'entrée."""

import logging

from app.main import main


class TestMainEntryPoint:
    """Vérifie que main() s'exécute sans erreur."""

    def test_main_runs_without_error(self, caplog):
        with caplog.at_level(logging.INFO):
            main()
        assert "APP_STARTED" in caplog.text
