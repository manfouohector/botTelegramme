"""Records partagés pour Feature Engineering."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class TeamMatchRecord:
    """Vue simplifiée d'un match terminé pour calcul de features."""

    match_id: int
    scheduled_at: datetime
    team_id: int
    opponent_id: int
    is_home: bool
    goals_scored: int
    goals_conceded: int
    stats: dict
