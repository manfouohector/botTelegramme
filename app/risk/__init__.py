"""Risk Engine — validation avant publication."""

__all__ = [
    "RiskEngine",
    "MatchRiskAssessment",
    "SelectionRiskResult",
    "RiskFactorItem",
    "RiskEngineError",
    "MatchNotFoundError",
]


def __getattr__(name: str):
    if name == "RiskEngine":
        from app.risk.risk_engine import RiskEngine
        return RiskEngine
    if name in ("MatchRiskAssessment", "SelectionRiskResult", "RiskFactorItem"):
        from app.risk.schemas import MatchRiskAssessment, RiskFactorItem, SelectionRiskResult
        mapping = {
            "MatchRiskAssessment": MatchRiskAssessment,
            "SelectionRiskResult": SelectionRiskResult,
            "RiskFactorItem": RiskFactorItem,
        }
        return mapping[name]
    if name == "RiskEngineError":
        from app.risk.exceptions import RiskEngineError
        return RiskEngineError
    if name == "MatchNotFoundError":
        from app.risk.exceptions import MatchNotFoundError
        return MatchNotFoundError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
