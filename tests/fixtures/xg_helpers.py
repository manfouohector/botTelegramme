"""Helpers pour tests xG Engine."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database.enums import DataStatus, MatchStatus
from app.models.football import Competition, Season, Team
from app.models.match import Match, MatchStatistic


def seed_xg_test_data(session: Session) -> dict:
    """Crée 12 matchs terminés avec stats tirs + 1 match cible."""
    comp = Competition(external_id=401, name="Ligue 1", country="France")
    session.add(comp)
    session.flush()

    season = Season(competition_id=comp.id, external_id=2025, name="2025/2026", is_current=True)
    session.add(season)
    session.flush()

    home = Team(external_id=201, name="Team Home", short_name="HOM")
    away = Team(external_id=202, name="Team Away", short_name="AWY")
    session.add_all([home, away])
    session.flush()

    base = datetime(2026, 3, 1, 15, 0, tzinfo=timezone.utc)
    ext_id = 60000

    # 12 matchs terminés avec stats tirs (24 enregistrements training)
    results = [
        (2, 1, 14, 6), (1, 1, 10, 4), (3, 0, 16, 5), (2, 2, 12, 3),
        (1, 0, 11, 4), (0, 1, 8, 3), (2, 1, 15, 7), (3, 2, 18, 8),
        (1, 1, 9, 4), (2, 0, 13, 5), (4, 1, 20, 9), (1, 2, 10, 6),
    ]

    for i, (hs, aws, home_shots, home_sot) in enumerate(results):
        away_shots = max(6, home_shots - 3)
        away_sot = max(2, home_sot - 2)
        m = Match(
            external_match_id=ext_id,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=home.id,
            away_team_id=away.id,
            scheduled_at=base + timedelta(days=i * 3),
            status=MatchStatus.FINISHED,
            home_score=hs,
            away_score=aws,
            data_status=DataStatus.FRESH,
        )
        session.add(m)
        session.flush()
        session.add(MatchStatistic(
            match_id=m.id, team_id=home.id,
            stats={"type_42": home_shots, "type_49": home_sot},
        ))
        session.add(MatchStatistic(
            match_id=m.id, team_id=away.id,
            stats={"type_42": away_shots, "type_49": away_sot},
        ))
        ext_id += 1

    target = Match(
        external_match_id=ext_id,
        competition_id=comp.id,
        season_id=season.id,
        home_team_id=home.id,
        away_team_id=away.id,
        scheduled_at=base + timedelta(days=40),
        status=MatchStatus.SCHEDULED,
        data_status=DataStatus.FRESH,
    )
    session.add(target)
    session.flush()

    return {"competition": comp, "season": season, "home": home, "away": away, "target_match": target}
