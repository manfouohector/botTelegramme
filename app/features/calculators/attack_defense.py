"""Calculateurs de features — attaque / défense."""

from app.features.schemas import AttackDefenseFeatures
from app.features.records import TeamMatchRecord

# Type IDs Sportmonks courants (documentés) — utilisés seulement si présents
# Shots = 42, Shots on target = 49 (vérifiés via docs statistics types)
STAT_TYPE_SHOTS = "type_42"
STAT_TYPE_SHOTS_ON_TARGET = "type_49"


def _extract_stat_value(stats: dict, key: str) -> float | None:
    if key not in stats:
        return None
    val = stats[key]
    if isinstance(val, (int, float)):
        return float(val)
    return None


def compute_attack_defense_features(records: list[TeamMatchRecord]) -> AttackDefenseFeatures:
    """Agrège buts et statistiques disponibles (sans inventer de xG)."""
    features = AttackDefenseFeatures()
    if not records:
        return features

    n = len(records)
    total_scored = sum(r.goals_scored for r in records)
    total_conceded = sum(r.goals_conceded for r in records)
    features.goals_scored_per_match = total_scored / n
    features.goals_conceded_per_match = total_conceded / n

    shots_sum = 0.0
    shots_count = 0
    sot_sum = 0.0
    sot_count = 0

    for rec in records:
        shots = _extract_stat_value(rec.stats, STAT_TYPE_SHOTS)
        if shots is not None:
            shots_sum += shots
            shots_count += 1
        sot = _extract_stat_value(rec.stats, STAT_TYPE_SHOTS_ON_TARGET)
        if sot is not None:
            sot_sum += sot
            sot_count += 1

    if shots_count > 0:
        features.shots_per_match = shots_sum / shots_count
        features.stats_available = True
    if sot_count > 0:
        features.shots_on_target_per_match = sot_sum / sot_count
        features.stats_available = True

    return features
