"""Tests unitaires — normalizer Odds API."""

import pytest

from app.prediction.constants import SELECTION_AWAY, SELECTION_DRAW, SELECTION_HOME
from app.value.odds_normalizer import normalize_odds_event
from tests.fixtures.odds_helpers import ODDS_API_EVENT


class TestOddsNormalizer:
    def test_normalize_h2h(self):
        odds = normalize_odds_event(ODDS_API_EVENT)
        h2h = [o for o in odds if o.market_code == "1X2"]
        assert len(h2h) == 3
        selections = {o.selection for o in h2h}
        assert selections == {SELECTION_HOME, SELECTION_DRAW, SELECTION_AWAY}

    def test_normalize_all_markets(self):
        odds = normalize_odds_event(ODDS_API_EVENT)
        markets = {o.market_code for o in odds}
        assert markets == {"1X2", "OU25", "BTTS"}

    def test_home_odds_value(self):
        odds = normalize_odds_event(ODDS_API_EVENT)
        home = next(o for o in odds if o.selection == SELECTION_HOME)
        assert home.decimal_odds == pytest.approx(1.70)
        assert home.bookmaker == "pinnacle"
