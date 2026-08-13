"""Normalisation des réponses Sportmonks vers nos DTO internes."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.collectors.exceptions import NormalizationError
from app.collectors.schemas import (
    NormalizedCompetition,
    NormalizedMatch,
    NormalizedMatchStatistic,
    NormalizedSeason,
    NormalizedTeam,
)
from app.database.enums import DataStatus, MatchStatus

# Mapping state_id Sportmonks → statut interne
# Source: https://docs.sportmonks.com/v3/definitions/states
STATE_ID_TO_STATUS: dict[int, MatchStatus] = {
    1: MatchStatus.SCHEDULED,   # NS
    2: MatchStatus.LIVE,        # INPLAY_1ST_HALF
    3: MatchStatus.LIVE,        # HT
    4: MatchStatus.LIVE,        # BREAK
    5: MatchStatus.FINISHED,    # FT
    6: MatchStatus.LIVE,        # INPLAY_ET
    7: MatchStatus.FINISHED,   # AET
    8: MatchStatus.FINISHED,   # FT_PEN
    9: MatchStatus.LIVE,        # INPLAY_PENALTIES
    10: MatchStatus.POSTPONED,
    11: MatchStatus.LIVE,       # SUSPENDED
    12: MatchStatus.CANCELLED,
    13: MatchStatus.SCHEDULED,  # TBA
    14: MatchStatus.FINISHED,   # WO
    15: MatchStatus.CANCELLED,  # ABANDONED
    16: MatchStatus.POSTPONED,  # DELAYED
    17: MatchStatus.FINISHED,   # AWARDED
    18: MatchStatus.LIVE,       # INTERRUPTED
    19: MatchStatus.SCHEDULED,  # AWAITING_UPDATES
    20: MatchStatus.CANCELLED,  # DELETED
    21: MatchStatus.LIVE,
    22: MatchStatus.LIVE,       # INPLAY_2ND_HALF
    25: MatchStatus.LIVE,
    26: MatchStatus.SCHEDULED,  # PENDING
}


def map_state_id(state_id: int | None) -> MatchStatus:
    if state_id is None:
        return MatchStatus.SCHEDULED
    return STATE_ID_TO_STATUS.get(state_id, MatchStatus.SCHEDULED)


def parse_starting_at(value: str | None, tz_name: str = "UTC") -> datetime:
    """Parse starting_at Sportmonks (UTC) en datetime timezone-aware."""
    if not value:
        raise NormalizationError("starting_at manquant")
    try:
        naive = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise NormalizationError(f"Format starting_at invalide : {value}") from exc
    utc_dt = naive.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(ZoneInfo(tz_name))


def _normalize_competition(raw: dict | None, league_id: int | None) -> NormalizedCompetition:
    if isinstance(raw, dict) and raw.get("id"):
        return NormalizedCompetition(
            external_id=int(raw["id"]),
            name=str(raw.get("name") or f"League {raw['id']}"),
            country=_extract_country_name(raw),
            code=raw.get("short_code"),
        )
    if league_id:
        return NormalizedCompetition(
            external_id=int(league_id),
            name=f"League {league_id}",
        )
    raise NormalizationError("league_id manquant")


def _extract_country_name(league: dict) -> str | None:
    country = league.get("country")
    if isinstance(country, dict):
        return country.get("name")
    return None


def _normalize_season(raw: dict | None, season_id: int | None, competition_external_id: int) -> NormalizedSeason:
    if isinstance(raw, dict) and raw.get("id"):
        return NormalizedSeason(
            external_id=int(raw["id"]),
            competition_external_id=competition_external_id,
            name=str(raw.get("name") or f"Season {raw['id']}"),
            is_current=bool(raw.get("is_current", False)),
        )
    if season_id:
        return NormalizedSeason(
            external_id=int(season_id),
            competition_external_id=competition_external_id,
            name=f"Season {season_id}",
        )
    raise NormalizationError("season_id manquant")


def _normalize_participants(participants: list | None) -> tuple[NormalizedTeam, NormalizedTeam]:
    if not participants or len(participants) < 2:
        raise NormalizationError("participants insuffisants (minimum 2 équipes)")

    home_raw = away_raw = None
    for p in participants:
        if not isinstance(p, dict):
            continue
        meta = p.get("meta") or {}
        location = meta.get("location") if isinstance(meta, dict) else None
        if location == "home":
            home_raw = p
        elif location == "away":
            away_raw = p

    # Fallback : ordre du tableau si meta.location absent
    if home_raw is None or away_raw is None:
        valid = [p for p in participants if isinstance(p, dict) and p.get("id")]
        if len(valid) < 2:
            raise NormalizationError("Impossible d'identifier home/away")
        home_raw = home_raw or valid[0]
        away_raw = away_raw or valid[1]

    return _normalize_team(home_raw), _normalize_team(away_raw)


def _normalize_team(raw: dict) -> NormalizedTeam:
    return NormalizedTeam(
        external_id=int(raw["id"]),
        name=str(raw.get("name") or f"Team {raw['id']}"),
        short_name=raw.get("short_code"),
    )


def _extract_scores(scores: list | None, home_ext_id: int, away_ext_id: int) -> tuple[int | None, int | None]:
    if not scores:
        return None, None

    home_goals: int | None = None
    away_goals: int | None = None

    for entry in scores:
        if not isinstance(entry, dict):
            continue
        description = str(entry.get("description", "")).upper()
        if description not in {"CURRENT", "2ND_HALF", "FT", "FULLTIME", "FULL TIME"}:
            continue

        score_obj = entry.get("score") or {}
        if isinstance(score_obj, dict):
            goals = score_obj.get("goals")
            participant = score_obj.get("participant")
            if goals is not None and participant in ("home", "away"):
                if participant == "home":
                    home_goals = int(goals)
                else:
                    away_goals = int(goals)
                continue

        participant_id = entry.get("participant_id")
        goals_val = None
        if isinstance(score_obj, dict):
            goals_val = score_obj.get("goals")
        if goals_val is None:
            continue
        if participant_id == home_ext_id:
            home_goals = int(goals_val)
        elif participant_id == away_ext_id:
            away_goals = int(goals_val)

    return home_goals, away_goals


def _normalize_statistics(
    statistics: list | None,
    home_ext_id: int,
    away_ext_id: int,
) -> list[NormalizedMatchStatistic]:
    if not statistics:
        return []

    by_team: dict[int, dict] = {home_ext_id: {}, away_ext_id: {}}

    for stat in statistics:
        if not isinstance(stat, dict):
            continue
        team_id = stat.get("participant_id")
        if team_id not in by_team:
            continue
        type_id = stat.get("type_id")
        data = stat.get("data") or {}
        value = data.get("value") if isinstance(data, dict) else data
        if type_id is not None:
            by_team[team_id][f"type_{type_id}"] = value

    result = []
    for team_id, stats in by_team.items():
        if stats:
            result.append(NormalizedMatchStatistic(team_external_id=team_id, stats=stats))
    return result


def _assess_data_status(
    has_participants: bool,
    has_statistics: bool,
    is_placeholder: bool,
) -> DataStatus:
    if is_placeholder:
        return DataStatus.INCOMPLETE
    if has_participants and has_statistics:
        return DataStatus.FRESH
    if has_participants:
        return DataStatus.INCOMPLETE
    return DataStatus.MISSING


def normalize_fixture(raw: dict, timezone: str = "UTC") -> NormalizedMatch:
    """Transforme une fixture Sportmonks brute en NormalizedMatch."""
    if not isinstance(raw, dict):
        raise NormalizationError("Fixture invalide (non-dict)")

    fixture_id = raw.get("id")
    if not fixture_id:
        raise NormalizationError("id fixture manquant")

    is_placeholder = bool(raw.get("placeholder", False))
    league_id = raw.get("league_id")
    season_id = raw.get("season_id")
    state_id = raw.get("state_id")

    competition = _normalize_competition(raw.get("league"), league_id)
    season = _normalize_season(raw.get("season"), season_id, competition.external_id)

    participants = raw.get("participants")
    has_participants = isinstance(participants, list) and len(participants) >= 2

    if not has_participants:
        raise NormalizationError(f"Fixture {fixture_id} : participants manquants")

    home_team, away_team = _normalize_participants(participants)
    home_score, away_score = _extract_scores(raw.get("scores"), home_team.external_id, away_team.external_id)

    statistics = _normalize_statistics(raw.get("statistics"), home_team.external_id, away_team.external_id)
    has_statistics = len(statistics) > 0

    status = map_state_id(state_id if isinstance(state_id, int) else None)
    data_status = _assess_data_status(has_participants, has_statistics, is_placeholder)

    return NormalizedMatch(
        external_match_id=int(fixture_id),
        competition=competition,
        season=season,
        home_team=home_team,
        away_team=away_team,
        scheduled_at=parse_starting_at(raw.get("starting_at"), timezone),
        status=status.value,
        home_score=home_score,
        away_score=away_score,
        data_status=data_status.value,
        statistics=statistics,
        raw_state_id=state_id if isinstance(state_id, int) else None,
        is_placeholder=is_placeholder,
        has_statistics=has_statistics,
        has_participants=has_participants,
    )
