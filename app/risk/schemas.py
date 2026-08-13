"""Schémas Risk Engine."""

from dataclasses import dataclass, field

from app.database.enums import ConfidenceLevel, RiskDecision


@dataclass
class RiskFactorItem:
    """Facteur de risque identifié."""

    factor: str
    impact: str
    severity: str

    def to_dict(self) -> dict:
        return {"factor": self.factor, "impact": self.impact, "severity": self.severity}


@dataclass
class SelectionRiskResult:
    """Résultat risk pour une sélection."""

    match_id: int
    market_code: str
    selection: str
    decision: RiskDecision
    confidence: ConfidenceLevel
    factors: list[RiskFactorItem] = field(default_factory=list)
    publishable: bool = False

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "market_code": self.market_code,
            "selection": self.selection,
            "decision": self.decision.value,
            "confidence": self.confidence.value,
            "publishable": self.publishable,
            "factors": [f.to_dict() for f in self.factors],
        }


@dataclass
class MatchRiskAssessment:
    """Évaluation risk complète pour un match."""

    match_id: int
    decision: RiskDecision
    confidence: ConfidenceLevel
    factors: list[RiskFactorItem] = field(default_factory=list)
    selections: list[SelectionRiskResult] = field(default_factory=list)
    publishable: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "decision": self.decision.value,
            "confidence": self.confidence.value,
            "publishable": self.publishable,
            "factors": [f.to_dict() for f in self.factors],
            "selections": [s.to_dict() for s in self.selections],
            "metadata": self.metadata,
        }
