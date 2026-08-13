"""Constantes Value Engine et Odds API."""

ODDS_API_PROVIDER = "odds_api"

# Marchés The Odds API → codes internes
ODDS_MARKET_H2H = "h2h"
ODDS_MARKET_TOTALS = "totals"
ODDS_MARKET_BTTS = "btts"

MARKET_MAP = {
    ODDS_MARKET_H2H: "1X2",
    ODDS_MARKET_TOTALS: "OU25",
    ODDS_MARKET_BTTS: "BTTS",
}

TOTALS_LINE = 2.5

# Sélections normalisées
DRAW_LABELS = frozenset({"draw", "tie", "x"})
