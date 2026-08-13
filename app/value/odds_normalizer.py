"""Normalisation The Odds API → DTOs internes."""

from __future__ import annotations

from datetime import datetime, timezone

from app.prediction.constants import (
    SELECTION_AWAY,
    SELECTION_DRAW,
    SELECTION_HOME,
    SELECTION_NO,
    SELECTION_OVER,
    SELECTION_UNDER,
    SELECTION_YES,
)
from app.value.constants import (
    DRAW_LABELS,
    MARKET_MAP,
    ODDS_MARKET_BTTS,
    ODDS_MARKET_H2H,
    ODDS_MARKET_TOTALS,
    TOTALS_LINE,
)
from app.value.exceptions import OddsAPIError
from app.value.schemas import NormalizedOdd


def normalize_odds_events(events: list[dict]) -> list[NormalizedOdd]:
    """Normalise une liste d'événements Odds API."""
    results: list[NormalizedOdd] = []
    for event in events:
        results.extend(normalize_odds_event(event))
    return results


def normalize_odds_event(event: dict) -> list[NormalizedOdd]:
    """Normalise un événement avec tous ses bookmakers."""
    event_id = str(event.get("id", ""))
    if not event_id:
        raise OddsAPIError("Événement Odds API sans id")

    sport_key = event.get("sport_key", "")
    home_team = event.get("home_team", "")
    away_team = event.get("away_team", "")
    commence_time = _parse_commence_time(event.get("commence_time"))

    normalized: list[NormalizedOdd] = []
    for bookmaker in event.get("bookmakers", []):
        bk_key = bookmaker.get("key") or bookmaker.get("title") or "unknown"
        for market in bookmaker.get("markets", []):
            market_key = market.get("key", "")
            internal_market = MARKET_MAP.get(market_key)
            if internal_market is None:
                continue

            for outcome in market.get("outcomes", []):
                selection = _map_selection(
                    market_key,
                    outcome,
                    home_team=home_team,
                    away_team=away_team,
                )
                if selection is None:
                    continue

                price = outcome.get("price")
                if price is None or float(price) <= 1.0:
                    continue

                point = outcome.get("point")
                if market_key == ODDS_MARKET_TOTALS and point is not None:
                    if abs(float(point) - TOTALS_LINE) > 0.01:
                        continue

                normalized.append(
                    NormalizedOdd(
                        external_event_id=event_id,
                        sport_key=sport_key,
                        home_team=home_team,
                        away_team=away_team,
                        commence_time=commence_time,
                        bookmaker=str(bk_key),
                        market_code=internal_market,
                        selection=selection,
                        decimal_odds=float(price),
                        point=float(point) if point is not None else None,
                    )
                )
    return normalized


def _map_selection(
    market_key: str,
    outcome: dict,
    *,
    home_team: str,
    away_team: str,
) -> str | None:
    name = str(outcome.get("name", "")).strip()
    name_lower = name.lower()

    if market_key == ODDS_MARKET_H2H:
        if name_lower in DRAW_LABELS or name == "Draw":
            return SELECTION_DRAW
        if _names_match(name, home_team):
            return SELECTION_HOME
        if _names_match(name, away_team):
            return SELECTION_AWAY
        return None

    if market_key == ODDS_MARKET_TOTALS:
        if name_lower.startswith("over"):
            return SELECTION_OVER
        if name_lower.startswith("under"):
            return SELECTION_UNDER
        return None

    if market_key == ODDS_MARKET_BTTS:
        if name_lower in ("yes", "oui"):
            return SELECTION_YES
        if name_lower in ("no", "non"):
            return SELECTION_NO
        return None

    return None


def _names_match(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


def _parse_commence_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OddsAPIError(f"commence_time invalide : {value}") from exc
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
