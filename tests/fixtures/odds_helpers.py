"""Fixture Odds API pour tests."""

ODDS_API_EVENT = {
    "id": "evt123",
    "sport_key": "soccer_france_ligue_one",
    "home_team": "PSG",
    "away_team": "OM",
    "commence_time": "2026-08-20T20:00:00Z",
    "bookmakers": [
        {
            "key": "pinnacle",
            "title": "Pinnacle",
            "markets": [
                {
                    "key": "h2h",
                    "outcomes": [
                        {"name": "PSG", "price": 1.70},
                        {"name": "Draw", "price": 4.50},
                        {"name": "OM", "price": 7.00},
                    ],
                },
                {
                    "key": "totals",
                    "outcomes": [
                        {"name": "Over", "price": 1.85, "point": 2.5},
                        {"name": "Under", "price": 1.95, "point": 2.5},
                    ],
                },
                {
                    "key": "btts",
                    "outcomes": [
                        {"name": "Yes", "price": 1.72},
                        {"name": "No", "price": 2.10},
                    ],
                },
            ],
        }
    ],
}
