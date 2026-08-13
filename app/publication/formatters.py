"""Formatage des messages Telegram pour coupons."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config.settings import Settings
from app.coupons.schemas import GeneratedCoupon
from app.database.enums import ConfidenceLevel, CouponType
from app.models.coupon import Coupon
from app.prediction.constants import (
    MARKET_1X2,
    MARKET_BTTS,
    MARKET_OU25,
    SELECTION_AWAY,
    SELECTION_DRAW,
    SELECTION_HOME,
    SELECTION_NO,
    SELECTION_OVER,
    SELECTION_UNDER,
    SELECTION_YES,
)
from app.publication.constants import CONFIRMATION_MESSAGE

COUPON_TITLES = {
    CouponType.FREE: "🟢 **COUPON GRATUIT**",
    CouponType.SAFE: "🛡 **COUPON SAFE**",
    CouponType.VALUE: "💎 **COUPON VALUE**",
    CouponType.HIGH_ODDS: "🎯 **COUPON HIGH ODDS**",
}


def _resolve_coupon_type(coupon_type: CouponType | str) -> CouponType:
    if isinstance(coupon_type, CouponType):
        return coupon_type
    return CouponType(coupon_type)

CONFIDENCE_LABELS = {
    ConfidenceLevel.HIGH: "Élevée",
    ConfidenceLevel.MEDIUM: "Moyenne",
    ConfidenceLevel.LOW: "Faible",
}


def format_selection_label(market_code: str, selection: str) -> str:
    code = market_code.upper()
    sel = selection.upper()
    if code == MARKET_1X2:
        return {
            SELECTION_HOME: "1",
            SELECTION_DRAW: "N",
            SELECTION_AWAY: "2",
        }.get(sel, sel)
    if code == MARKET_BTTS:
        return "Oui" if sel == SELECTION_YES else "Non"
    if code == MARKET_OU25:
        return "+2.5 buts" if sel == SELECTION_OVER else "-2.5 buts"
    return sel


def _format_match_time(scheduled_at: datetime | None, timezone_name: str) -> str:
    if scheduled_at is None:
        return ""
    dt = scheduled_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    local = dt.astimezone(ZoneInfo(timezone_name))
    return local.strftime("%d/%m %H:%M")


def _combined_odds_from_coupon(coupon: Coupon) -> float:
    total = 1.0
    for link in sorted(coupon.predictions, key=lambda item: item.position):
        pred = link.prediction
        if pred and pred.odds is not None:
            total *= float(pred.odds)
    return total


def _combined_odds_from_generated(generated: GeneratedCoupon) -> float:
    total = 1.0
    for candidate in generated.candidates:
        total *= candidate.decimal_odds
    return total


def format_confirmation_message(coupon_type: CouponType, *, version: int = 1) -> str:
    labels = {
        CouponType.FREE: "COUPON GRATUIT",
        CouponType.SAFE: "COUPON SAFE",
        CouponType.VALUE: "COUPON VALUE",
        CouponType.HIGH_ODDS: "COUPON HIGH ODDS",
    }
    label = labels.get(coupon_type, coupon_type.value)
    return f"✅ **{label} V{version}**\n\n{CONFIRMATION_MESSAGE}"


def format_coupon_message(
    coupon: Coupon,
    settings: Settings,
    *,
    detailed: bool = True,
) -> str:
    """Formate un coupon persisté pour Telegram."""
    coupon_type = _resolve_coupon_type(coupon.type)
    title = COUPON_TITLES.get(coupon_type, f"**{coupon_type.value}**")
    lines = [title, f"_Version {coupon.version}_", ""]

    combined = _combined_odds_from_coupon(coupon)
    links = sorted(coupon.predictions, key=lambda link: link.position)

    for index, link in enumerate(links, start=1):
        pred = link.prediction
        if pred is None or pred.market is None:
            continue
        match = pred.match
        home = match.home_team.name if match and match.home_team else "?"
        away = match.away_team.name if match and match.away_team else "?"
        kickoff = _format_match_time(match.scheduled_at if match else None, settings.timezone)
        selection = format_selection_label(pred.market.code, pred.selection)
        odds = float(pred.odds) if pred.odds is not None else 0.0

        if detailed and coupon_type != CouponType.FREE:
            prob_pct = float(pred.probability) * 100
            conf = CONFIDENCE_LABELS.get(pred.confidence, str(pred.confidence))
            time_suffix = f" ({kickoff})" if kickoff else ""
            lines.extend(
                [
                    f"**{index}. {home} vs {away}**{time_suffix}",
                    f"• Pari : {pred.market.code} — {selection}",
                    f"• Cote : {odds:.2f}",
                    f"• Probabilité : {prob_pct:.1f}%",
                    f"• Confiance : {conf}",
                    "",
                ]
            )
        else:
            time_suffix = f" — {kickoff}" if kickoff else ""
            lines.append(f"**{index}.** {home} vs {away}{time_suffix} — {selection} @ {odds:.2f}")

    lines.append(f"**Cote combinée : {combined:.2f}**")
    lines.append("")
    lines.append(f"_{settings.app_name}_")
    return "\n".join(lines)


def format_generated_coupon_preview(
    generated: GeneratedCoupon,
    settings: Settings,
    *,
    detailed: bool = True,
) -> str:
    """Formate un coupon généré (candidats) avant/après persistance."""
    title = COUPON_TITLES.get(generated.coupon_type, generated.coupon_type.value)
    lines = [title, ""]

    for index, candidate in enumerate(generated.candidates, start=1):
        selection = format_selection_label(candidate.market_code, candidate.selection)
        if detailed and generated.coupon_type != CouponType.FREE:
            prob_pct = candidate.probability * 100
            conf = CONFIDENCE_LABELS.get(candidate.confidence, candidate.confidence.value)
            lines.extend(
                [
                    f"**{index}. {candidate.home_team} vs {candidate.away_team}**",
                    f"• Pari : {candidate.market_code} — {selection}",
                    f"• Cote : {candidate.decimal_odds:.2f}",
                    f"• Probabilité : {prob_pct:.1f}%",
                    f"• Confiance : {conf}",
                    "",
                ]
            )
        else:
            lines.append(
                f"**{index}.** {candidate.home_team} vs {candidate.away_team} "
                f"— {selection} @ {candidate.decimal_odds:.2f}"
            )

    combined = _combined_odds_from_generated(generated)
    lines.append(f"**Cote combinée : {combined:.2f}**")
    lines.append("")
    lines.append(f"_{settings.app_name}_")
    return "\n".join(lines)
