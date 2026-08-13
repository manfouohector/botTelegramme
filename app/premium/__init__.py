"""Premium — activation et statut."""

__all__ = [
    "PremiumService",
    "ActivationResult",
    "PremiumStatus",
    "PremiumError",
]


def __getattr__(name: str):
    if name == "PremiumService":
        from app.services.premium_service import PremiumService
        return PremiumService
    if name in ("ActivationResult", "PremiumStatus"):
        from app.premium.schemas import ActivationResult, PremiumStatus
        return {"ActivationResult": ActivationResult, "PremiumStatus": PremiumStatus}[name]
    if name == "PremiumError":
        from app.premium.exceptions import PremiumError
        return PremiumError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
