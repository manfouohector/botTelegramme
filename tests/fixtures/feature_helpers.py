"""Helpers pour tests Feature Engineering."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database.enums import DataStatus, MatchStatus
from app.models.football import Competition, Season, Team
from app.models.match import Match, MatchStatistic


def seed_feature_test_data(session: Session) -> dict:
    """
    Crée un jeu de données historique pour tester les features.

    Scénario : PSG vs OM le 2026-08-20
    Historique : 5 matchs terminés avant cette date pour chaque équipe.
    """
    comp = Competition(external_id=301, name="Ligue 1", country="France")
    session.add(comp)
    session.flush()

    season = Season(competition_id=comp.id, external_id=2025, name="2025/2026", is_current=True)
    session.add(season)
    session.flush()

    psg = Team(external_id=100, name="PSG", short_name="PSG")
    om = Team(external_id=101, name="OM", short_name="OM")
    lyon = Team(external_id=102, name="Lyon", short_name="LYO")
    lille = Team(external_id=103, name="Lille", short_name="LIL")
    session.add_all([psg, om, lyon, lille])
    session.flush()

    base_date = datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc)

    # PSG historique (4V 1D) — domicile
    psg_results = [
        (3, 1), (2, 0), (1, 1), (4, 2), (2, 1),
    ]
    opponents = [lyon, lille, om, lyon, lille]

    match_ids = []
    for i, ((hs, aws), opp) in enumerate(zip(psg_results, opponents)):
        m = Match(
            external_match_id=10000 + i,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=psg.id,
            away_team_id=opp.id,
            scheduled_at=base_date + timedelta(days=i * 3),
            status=MatchStatus.FINISHED,
            home_score=hs,
            away_score=aws,
            data_status=DataStatus.FRESH,
        )
        session.add(m)
        session.flush()
        session.add(MatchStatistic(match_id=m.id, team_id=psg.id, stats={"type_42": 12 + i, "type_49": 5}))
        match_ids.append(m.id)

    # OM historique (2V 2D 1L) — extérieur
    om_results = [
        (0, 1), (2, 2), (1, 0), (1, 1), (0, 2),
    ]
    om_opponents = [lyon, lille, lyon, lille, lyon]

    for i, ((hs, aws), opp) in enumerate(zip(om_results, om_opponents)):
        m = Match(
            external_match_id=20000 + i,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=opp.id,
            away_team_id=om.id,
            scheduled_at=base_date + timedelta(days=i * 3 + 1),
            status=MatchStatus.FINISHED,
            home_score=hs,
            away_score=aws,
            data_status=DataStatus.FRESH,
        )
        session.add(m)
        session.flush()
        session.add(MatchStatistic(match_id=m.id, team_id=om.id, stats={"type_42": 8}))

    # H2H : PSG 2-1 OM (PSG domicile)
    h2h = Match(
        external_match_id=30001,
        competition_id=comp.id,
        season_id=season.id,
        home_team_id=psg.id,
        away_team_id=om.id,
        scheduled_at=base_date + timedelta(days=10),
        status=MatchStatus.FINISHED,
        home_score=2,
        away_score=1,
        data_status=DataStatus.FRESH,
    )
    session.add(h2h)
    session.flush()

    # Match FUTUR (leakage test) — PSG 5-0 OM après le match cible
    future = Match(
        external_match_id=30002,
        competition_id=comp.id,
        season_id=season.id,
        home_team_id=psg.id,
        away_team_id=om.id,
        scheduled_at=datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc),
        status=MatchStatus.FINISHED,
        home_score=5,
        away_score=0,
        data_status=DataStatus.FRESH,
    )
    session.add(future)

    # Match CIBLE à prédire
    target = Match(
        external_match_id=99999,
        competition_id=comp.id,
        season_id=season.id,
        home_team_id=psg.id,
        away_team_id=om.id,
        scheduled_at=datetime(2026, 8, 20, 20, 0, tzinfo=timezone.utc),
        status=MatchStatus.SCHEDULED,
        data_status=DataStatus.FRESH,
    )
    session.add(target)
    session.flush()

    return {
        "competition": comp,
        "season": season,
        "psg": psg,
        "om": om,
        "target_match": target,
        "h2h_match": h2h,
        "future_match": future,
    }
