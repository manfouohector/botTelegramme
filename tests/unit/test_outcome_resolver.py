"""Tests unitaires — outcome resolver."""

import pytest

from app.prediction.constants import (
    MARKET_1X2,
    MARKET_BTTS,
    MARKET_OU25,
    SELECTION_AWAY,
    SELECTION_DRAW,
    SELECTION_HOME,
    SELECTION_NO,
    SELECTION_OVER,
    SELECTION_UNDER,
    SELECTION_YES,
)
from app.tracking.exceptions import TrackingError
from app.tracking.outcome_resolver import resolve_all_outcomes, resolve_market_outcome


class TestOutcomeResolver:
    def test_1x2_home_win(self):
        assert resolve_market_outcome(MARKET_1X2, 2, 1) == SELECTION_HOME

    def test_1x2_draw(self):
        assert resolve_market_outcome(MARKET_1X2, 1, 1) == SELECTION_DRAW

    def test_1x2_away_win(self):
        assert resolve_market_outcome(MARKET_1X2, 0, 2) == SELECTION_AWAY

    def test_btts_yes(self):
        assert resolve_market_outcome(MARKET_BTTS, 2, 1) == SELECTION_YES

    def test_btts_no(self):
        assert resolve_market_outcome(MARKET_BTTS, 1, 0) == SELECTION_NO

    def test_ou25_over(self):
        assert resolve_market_outcome(MARKET_OU25, 2, 1) == SELECTION_OVER

    def test_ou25_under(self):
        assert resolve_market_outcome(MARKET_OU25, 1, 0) == SELECTION_UNDER

    def test_resolve_all_outcomes(self):
        outcomes = resolve_all_outcomes(3, 2)
        assert outcomes[MARKET_1X2] == SELECTION_HOME
        assert outcomes[MARKET_BTTS] == SELECTION_YES
        assert outcomes[MARKET_OU25] == SELECTION_OVER

    def test_unknown_market_raises(self):
        with pytest.raises(TrackingError):
            resolve_market_outcome("UNKNOWN", 1, 0)
