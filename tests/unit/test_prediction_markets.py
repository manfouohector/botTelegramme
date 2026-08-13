"""Tests unitaires — marchés dérivés."""

from app.prediction.constants import MARKET_1X2, MARKET_BTTS, MARKET_OU25, SELECTION_AWAY, SELECTION_DRAW, SELECTION_HOME
from app.prediction.markets import derive_markets, ensemble_1x2
from app.prediction.poisson import build_score_matrix


class TestMarkets:
    def test_1x2_sums_to_one(self):
        matrix = build_score_matrix(1.4, 1.2)
        markets = derive_markets(matrix, model_type="POISSON", enabled_markets=(MARKET_1X2,))
        m1x2 = markets[0]
        assert abs(sum(m1x2.probabilities.values()) - 1.0) < 1e-9
        assert SELECTION_HOME in m1x2.probabilities

    def test_btts_and_ou25(self):
        matrix = build_score_matrix(1.8, 1.5)
        markets = derive_markets(
            matrix, model_type="POISSON", enabled_markets=(MARKET_BTTS, MARKET_OU25)
        )
        assert len(markets) == 2
        btts = next(m for m in markets if m.market_code == MARKET_BTTS)
        assert abs(sum(btts.probabilities.values()) - 1.0) < 1e-9

    def test_ensemble_1x2(self):
        poisson = {SELECTION_HOME: 0.6, SELECTION_DRAW: 0.25, SELECTION_AWAY: 0.15}
        ml = {SELECTION_HOME: 0.5, SELECTION_DRAW: 0.3, SELECTION_AWAY: 0.2}
        blended = ensemble_1x2(poisson, ml, poisson_weight=0.5)
        assert abs(sum(blended.values()) - 1.0) < 1e-9
        assert blended[SELECTION_HOME] == 0.55
