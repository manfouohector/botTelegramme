"""Règles de risque — une fonction par contrôle."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.calibration.schemas import CalibratedMatchPrediction
from app.config.settings import Settings
from app.database.enums import ConfidenceLevel, DataStatus
from app.models.match import Match
from app.models.player import Injury, Lineup
from app.prediction.schemas import MatchPrediction
from app.risk.constants import (
    FACTOR_EXTREME_EDGE,
    FACTOR_HIGH_STAKES,
    FACTOR_INCOMPLETE_DATA,
    FACTOR_INJURIES_UNCONFIRMED,
    FACTOR_INSUFFICIENT_HISTORY,
    FACTOR_LINEUPS_MISSING,
    FACTOR_LOW_CONFIDENCE,
    FACTOR_LOW_DATA_QUALITY,
    FACTOR_LOW_EDGE,
    FACTOR_MODEL_DISAGREEMENT,
    FACTOR_NO_ODDS,
    FACTOR_NO_VALUE,
    FACTOR_STALE_DATA,
    FACTOR_XG_UNAVAILABLE,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)
from app.risk.schemas import RiskFactorItem
from app.value.schemas import MatchValueAnalysis, ValueOpportunity
from app.xg.constants import MODEL_UNAVAILABLE


def evaluate_match_factors(
    session: Session,
    match: Match,
    prediction: MatchPrediction | CalibratedMatchPrediction,
    *,
    settings: Settings,
) -> list[RiskFactorItem]:
    """Facteurs de risque au niveau match."""
    factors: list[RiskFactorItem] = []
    factors.extend(_check_confidence(prediction.confidence, settings))
    factors.extend(_check_data_status(match, settings))
    factors.extend(_check_prediction_quality(prediction, settings))
    factors.extend(_check_context(prediction))
    factors.extend(_check_injuries(session, match.id, settings))
    factors.extend(_check_lineups(session, match.id, settings))
    return factors


def evaluate_selection_factors(
    opportunity: ValueOpportunity | None,
    value_analysis: MatchValueAnalysis | None,
    *,
    settings: Settings,
) -> list[RiskFactorItem]:
    """Facteurs de risque spécifiques à une sélection value."""
    factors: list[RiskFactorItem] = []

    if opportunity is None and value_analysis is None:
        factors.append(
            RiskFactorItem(
                factor=FACTOR_NO_ODDS,
                impact="Aucune cote bookmaker disponible",
                severity=SEVERITY_MEDIUM,
            )
        )
        return factors

    if value_analysis is None and opportunity is not None:
        pass  # évaluation sur opportunité explicite sans analyse complète
    elif value_analysis is None:
        factors.append(
            RiskFactorItem(
                factor=FACTOR_NO_ODDS,
                impact="Aucune cote bookmaker disponible",
                severity=SEVERITY_MEDIUM,
            )
        )
        return factors

    if opportunity is None:
        factors.append(
            RiskFactorItem(
                factor=FACTOR_NO_VALUE,
                impact="Aucune opportunité value au-dessus du seuil",
                severity=SEVERITY_MEDIUM,
            )
        )
        return factors

    if not opportunity.is_value:
        factors.append(
            RiskFactorItem(
                factor=FACTOR_LOW_EDGE,
                impact=f"Edge {opportunity.value_edge:.1%} sous le seuil",
                severity=SEVERITY_HIGH,
            )
        )

    if opportunity.value_edge >= settings.risk_max_edge_threshold:
        factors.append(
            RiskFactorItem(
                factor=FACTOR_EXTREME_EDGE,
                impact=f"Edge suspect ({opportunity.value_edge:.1%}) — vérifier données",
                severity=SEVERITY_MEDIUM,
            )
        )

    return factors


def aggregate_decision(
    factors: list[RiskFactorItem],
    confidence: ConfidenceLevel,
    settings: Settings,
):
    """Retourne APPROVE, WARNING ou REJECT."""
    from app.database.enums import RiskDecision

    if any(f.severity == SEVERITY_HIGH for f in factors):
        return RiskDecision.REJECT

    if confidence == ConfidenceLevel.LOW and settings.risk_reject_low_confidence:
        return RiskDecision.REJECT

    if any(f.severity == SEVERITY_MEDIUM for f in factors):
        return RiskDecision.WARNING

    return RiskDecision.APPROVE


def is_publishable(decision) -> bool:
    from app.database.enums import RiskDecision

    value = decision.value if hasattr(decision, "value") else decision
    return value in (RiskDecision.APPROVE.value, RiskDecision.WARNING.value)


def _check_confidence(confidence: ConfidenceLevel, settings: Settings) -> list[RiskFactorItem]:
    if confidence == ConfidenceLevel.LOW:
        severity = SEVERITY_HIGH if settings.risk_reject_low_confidence else SEVERITY_MEDIUM
        return [
            RiskFactorItem(
                factor=FACTOR_LOW_CONFIDENCE,
                impact="Confiance LOW — données ou cohérence insuffisantes",
                severity=severity,
            )
        ]
    if confidence == ConfidenceLevel.MEDIUM:
        return [
            RiskFactorItem(
                factor=FACTOR_LOW_CONFIDENCE,
                impact="Confiance MEDIUM — prudence recommandée",
                severity=SEVERITY_LOW,
            )
        ]
    return []


def _check_data_status(match: Match, settings: Settings) -> list[RiskFactorItem]:
    factors: list[RiskFactorItem] = []

    if match.data_status in (DataStatus.INCOMPLETE, DataStatus.MISSING, DataStatus.ERROR):
        if settings.risk_reject_incomplete_data:
            factors.append(
                RiskFactorItem(
                    factor=FACTOR_INCOMPLETE_DATA,
                    impact=f"Statut données : {match.data_status.value}",
                    severity=SEVERITY_HIGH,
                )
            )

    if match.data_status == DataStatus.STALE and settings.risk_reject_stale_data:
        factors.append(
            RiskFactorItem(
                factor=FACTOR_STALE_DATA,
                impact="Données marquées STALE",
                severity=SEVERITY_MEDIUM,
            )
        )

    if match.last_fetched_at and settings.risk_stale_data_hours > 0:
        fetched = match.last_fetched_at
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - fetched
        if age > timedelta(hours=settings.risk_stale_data_hours):
            factors.append(
                RiskFactorItem(
                    factor=FACTOR_STALE_DATA,
                    impact=f"Dernière collecte il y a {int(age.total_seconds() // 3600)}h",
                    severity=SEVERITY_MEDIUM if settings.risk_reject_stale_data else SEVERITY_LOW,
                )
            )

    return factors


def _check_prediction_quality(
    prediction: MatchPrediction | CalibratedMatchPrediction,
    settings: Settings,
) -> list[RiskFactorItem]:
    factors: list[RiskFactorItem] = []
    meta = prediction.metadata if hasattr(prediction, "metadata") else {}
    if isinstance(prediction, CalibratedMatchPrediction):
        meta = {**prediction.raw.metadata, **prediction.metadata}

    features_snap = prediction.features_snapshot if hasattr(prediction, "features_snapshot") else {}
    if isinstance(prediction, CalibratedMatchPrediction):
        features_snap = prediction.raw.features_snapshot

    data_quality = meta.get("data_quality_features") or features_snap.get("features", {}).get(
        "data_quality"
    )
    if data_quality == "LOW":
        factors.append(
            RiskFactorItem(
                factor=FACTOR_LOW_DATA_QUALITY,
                impact="Qualité features LOW",
                severity=SEVERITY_MEDIUM,
            )
        )

    matches_home = features_snap.get("features", {}).get("matches_used_home")
    matches_away = features_snap.get("features", {}).get("matches_used_away")
    if (
        matches_home is not None
        and matches_away is not None
        and (matches_home < settings.prediction_min_matches or matches_away < settings.prediction_min_matches)
    ):
        factors.append(
            RiskFactorItem(
                factor=FACTOR_INSUFFICIENT_HISTORY,
                impact=f"Historique insuffisant ({matches_home}/{matches_away} matchs)",
                severity=SEVERITY_MEDIUM,
            )
        )

    if meta.get("data_quality_xg") == "UNAVAILABLE" or meta.get("data_quality_xg") == "LOW":
        xg_info = features_snap.get("xg", {})
        if not xg_info or xg_info.get("model_type") == MODEL_UNAVAILABLE:
            factors.append(
                RiskFactorItem(
                    factor=FACTOR_XG_UNAVAILABLE,
                    impact="xG proxy indisponible",
                    severity=SEVERITY_LOW,
                )
            )

    if meta.get("ml_trained") and meta.get("ml_sample_size", 0) > 0:
        poisson_w = settings.prediction_ensemble_poisson_weight
        if poisson_w < 1.0 and meta.get("model_type") == "ENSEMBLE":
            pass  # ensemble ok
        elif meta.get("poisson_model"):
            pass

    if meta.get("ml_trained") is False and settings.prediction_enable_ml:
        factors.append(
            RiskFactorItem(
                factor=FACTOR_MODEL_DISAGREEMENT,
                impact="Modèle ML non entraîné — Poisson seul",
                severity=SEVERITY_LOW,
            )
        )

    return factors


def _check_context(prediction: MatchPrediction | CalibratedMatchPrediction) -> list[RiskFactorItem]:
    if isinstance(prediction, CalibratedMatchPrediction):
        features_snap = prediction.raw.features_snapshot
    else:
        features_snap = prediction.features_snapshot

    ctx = features_snap.get("context", {})
    factor_list = ctx.get("factors", [])
    for item in factor_list:
        if item.get("name") == "high_stakes" and float(item.get("value", 0)) >= 1.0:
            return [
                RiskFactorItem(
                    factor=FACTOR_HIGH_STAKES,
                    impact="Match à enjeu élevé (derby/titre/maintien/coupe)",
                    severity=SEVERITY_LOW,
                )
            ]
    return []


def _check_injuries(session: Session, match_id: int, settings: Settings) -> list[RiskFactorItem]:
    if not settings.risk_check_injuries:
        return []

    count = session.scalar(
        select(func.count()).select_from(Injury).where(Injury.match_id == match_id)
    )
    if count and count > 0:
        return []

    return [
        RiskFactorItem(
            factor=FACTOR_INJURIES_UNCONFIRMED,
            impact="Aucune donnée blessures enregistrée",
            severity=SEVERITY_LOW,
        )
    ]


def _check_lineups(session: Session, match_id: int, settings: Settings) -> list[RiskFactorItem]:
    if not settings.risk_check_lineups:
        return []

    count = session.scalar(
        select(func.count()).select_from(Lineup).where(Lineup.match_id == match_id)
    )
    if count and count >= 2:
        return []

    return [
        RiskFactorItem(
            factor=FACTOR_LINEUPS_MISSING,
            impact="Compositions non disponibles",
            severity=SEVERITY_LOW,
        )
    ]
