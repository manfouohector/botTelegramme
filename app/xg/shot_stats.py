"""Extraction des statistiques de tirs depuis match_statistics."""

from app.features.records import TeamMatchRecord
from app.xg.constants import STAT_TYPE_SHOTS, STAT_TYPE_SHOTS_ON_TARGET
from app.xg.schemas import ShotStats


def extract_shot_stats(stats: dict) -> ShotStats:
    """Extrait tirs et tirs cadrés des stats Sportmonks normalisées."""
    shots = _to_float(stats.get(STAT_TYPE_SHOTS))
    sot = _to_float(stats.get(STAT_TYPE_SHOTS_ON_TARGET))
    return ShotStats(shots=shots, shots_on_target=sot)


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def average_shot_stats(records: list[TeamMatchRecord]) -> ShotStats:
    """Moyenne des tirs sur une fenêtre de matchs."""
    shots_vals: list[float] = []
    sot_vals: list[float] = []

    for rec in records:
        ss = extract_shot_stats(rec.stats)
        if ss.shots is not None:
            shots_vals.append(ss.shots)
        if ss.shots_on_target is not None:
            sot_vals.append(ss.shots_on_target)

    return ShotStats(
        shots=sum(shots_vals) / len(shots_vals) if shots_vals else None,
        shots_on_target=sum(sot_vals) / len(sot_vals) if sot_vals else None,
    )


def records_with_shot_data(records: list[TeamMatchRecord]) -> list[TeamMatchRecord]:
    return [r for r in records if extract_shot_stats(r.stats).has_data]
