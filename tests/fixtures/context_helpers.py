"""Helpers pour tests Context Engine."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database.enums import DataStatus, MatchStatus
from app.models.football import Competition, Season, Team
from app.models.match import Match


def seed_context_test_data(session: Session) -> dict:
    """
    Scénario : PSG (2e, 61 pts) vs Amiens (18e, 24 pts), 5 journées restantes.

    6 équipes, 33 journées simulées via matchs terminés + matchs scheduled restants.
    """
    comp = Competition(external_id=301, name="Ligue 1", country="France")
    session.add(comp)
    session.flush()

    season = Season(competition_id=comp.id, external_id=2025, name="2025/2026", is_current=True)
    session.add(season)
    session.flush()

    teams_config = [
        (100, "Leader FC", 66),
        (101, "PSG", 61),
        (102, "Lyon", 55),
        (103, "Lille", 50),
        (104, "Nice", 40),
        (105, "Amiens", 24),
    ]
    teams: dict[str, Team] = {}
    for ext_id, name, _ in teams_config:
        t = Team(external_id=ext_id, name=name, short_name=name[:3])
        session.add(t)
        teams[name] = t
    session.flush()

    base = datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc)
    ext_id = 50000

    # Round-robin simplifié : chaque paire joue 2 matchs (aller/retour) avec scores fixés
    # pour produire le classement cible approximatif
    fixtures = [
        # Leader gagne beaucoup
        ("Leader FC", "PSG", 2, 1), ("PSG", "Leader FC", 1, 1),
        ("Leader FC", "Lyon", 3, 0), ("Lyon", "Leader FC", 0, 2),
        ("Leader FC", "Lille", 2, 0), ("Lille", "Leader FC", 1, 2),
        ("Leader FC", "Nice", 3, 1), ("Nice", "Leader FC", 0, 2),
        ("Leader FC", "Amiens", 4, 0), ("Amiens", "Leader FC", 0, 3),
        # PSG
        ("PSG", "Lyon", 2, 0), ("Lyon", "PSG", 1, 1),
        ("PSG", "Lille", 3, 1), ("Lille", "PSG", 0, 1),
        ("PSG", "Nice", 2, 1), ("Nice", "PSG", 1, 2),
        ("PSG", "Amiens", 5, 0), ("Amiens", "PSG", 0, 4),
        # Lyon, Lille, Nice entre eux
        ("Lyon", "Lille", 2, 1), ("Lille", "Lyon", 1, 1),
        ("Lyon", "Nice", 2, 0), ("Nice", "Lyon", 1, 1),
        ("Lille", "Nice", 1, 0), ("Nice", "Lille", 0, 1),
        # Amiens perd
        ("Lyon", "Amiens", 3, 0), ("Amiens", "Lyon", 0, 2),
        ("Lille", "Amiens", 2, 0), ("Amiens", "Lille", 1, 3),
        ("Nice", "Amiens", 2, 1), ("Amiens", "Nice", 0, 1),
    ]

    day = 0
    for home_name, away_name, hs, aws in fixtures:
        m = Match(
            external_match_id=ext_id,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=teams[home_name].id,
            away_team_id=teams[away_name].id,
            scheduled_at=base + timedelta(days=day),
            status=MatchStatus.FINISHED,
            home_score=hs,
            away_score=aws,
            data_status=DataStatus.FRESH,
        )
        session.add(m)
        ext_id += 1
        day += 3
    session.flush()

    # 5 matchs restants (scheduled) — le match cible est le premier
    remaining_opponents = ["Amiens", "Lyon", "Lille", "Nice", "Leader FC"]
    target_date = base + timedelta(days=day)
    target = None
    for i, opp_name in enumerate(remaining_opponents):
        scheduled = target_date + timedelta(days=i * 7)
        m = Match(
            external_match_id=ext_id,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=teams["PSG"].id,
            away_team_id=teams[opp_name].id,
            scheduled_at=scheduled,
            status=MatchStatus.SCHEDULED,
            data_status=DataStatus.FRESH,
        )
        session.add(m)
        if i == 0:
            target = m
        ext_id += 1
    session.flush()

    return {
        "competition": comp,
        "season": season,
        "psg": teams["PSG"],
        "amiens": teams["Amiens"],
        "target_match": target,
    }
