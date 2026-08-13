"""Messages commandes admin — /generate, /status, /history."""

from __future__ import annotations

from app.database.enums import CouponType
from app.generation.schemas import DailyStatus, GenerationBatchResult, HistoryDaySummary


def _format_date_fr(value) -> str:
    return value.strftime("%d/%m/%Y")


def _yes_no(flag: bool) -> str:
    return "OUI" if flag else "NON"


def _coupon_type_label(coupon_type: CouponType) -> str:
    if coupon_type == CouponType.HIGH_ODDS:
        return "HIGH ODDS"
    return coupon_type.value


def format_generation_result(result: GenerationBatchResult) -> str:
    lines = [
        f"✅ **Génération terminée — {_format_date_fr(result.target_date)}**",
        "",
        f"• Matchs analysés : {result.matches_analyzed}",
        f"• Prédictions créées : {result.predictions_created}",
        f"• Coupons créés : {result.coupons_created}",
    ]

    if result.failed_stage:
        lines.extend(["", f"⚠️ Avertissement ({result.failed_stage}) : {result.error_message or '—'}"])

    if result.coupon_result:
        for generated in result.coupon_result.all_coupons():
            label = _coupon_type_label(generated.coupon_type)
            lines.append(f"• {label} : {len(generated.candidates)} sélections")
        for ctype, reason in result.skip_reasons.items():
            label = ctype.replace("_", " ")
            lines.append(f"• {label} : non créé — {reason}")

    lines.extend(
        [
            "",
            f"Publication Telegram : {_yes_no(result.published)}",
        ]
    )
    if result.publication_deferred:
        lines.append("(Publication désactivée ou Telegram non configuré)")
    elif result.publication_result is not None:
        pub = result.publication_result
        published = getattr(pub, "published_count", 0)
        confirmed = sum(1 for i in getattr(pub, "items", []) if getattr(i, "confirmed_only", False))
        if published:
            lines.append(f"• Messages publiés : {published}")
        if confirmed:
            lines.append(f"• Confirmations (inchangé) : {confirmed}")

    if result.system_run_id:
        lines.append(f"\nRun #{result.system_run_id}")
    return "\n".join(lines)


def format_generation_error(result: GenerationBatchResult) -> str:
    module = result.failed_stage or "Pipeline"
    detail = result.error_message or "erreur inconnue"
    return (
        f"❌ **Erreur de génération**\n\n"
        f"Module :\n{module}\n\n"
        f"Erreur :\n{detail}"
    )


def format_daily_status(status: DailyStatus) -> str:
    if status.no_matches_today:
        return "Aucun match aujourd'hui."

    if status.generation_error:
        module = status.failed_module or "Pipeline"
        detail = status.error_detail or "erreur inconnue"
        lines = [
            "Erreur de génération.",
            "",
            "Module :",
            module,
            "",
            "Erreur :",
            detail,
            "",
            f"Publication :\n{_yes_no(status.published)}",
        ]
        return "\n".join(lines)

    lines = [
        f"**STATUT DU {_format_date_fr(status.target_date)}**",
        "",
        f"Matchs récupérés : {status.matches_fetched}",
        f"Matchs analysés : {status.matches_analyzed}",
        f"Prédictions créées : {status.predictions_created}",
        "",
    ]

    for coupon in status.coupons:
        label = _coupon_type_label(coupon.coupon_type)
        lines.append(f"**{label}** :")
        lines.append(f"créé = {_yes_no(coupon.created)}")
        lines.append(f"envoyé = {_yes_no(coupon.sent)}")
        if not coupon.created and coupon.skip_reason:
            lines.extend(["", "Raison :", coupon.skip_reason])
        lines.append("")

    lines.append(f"Publication :\n{_yes_no(status.published)}")
    return "\n".join(lines).strip()


def format_history_summary(summary: HistoryDaySummary) -> str:
    if not summary.has_data:
        return "Aucun historique disponible pour le moment."

    lines = [
        f"**HISTORIQUE — {_format_date_fr(summary.target_date)}**",
        "",
    ]

    for entry in summary.by_type:
        label = _coupon_type_label(entry.coupon_type)
        lines.append(f"**{label}** :")
        lines.append(entry.display_ratio)
        lines.append("")

    lines.extend(
        [
            "**Résumé :**",
            "",
            f"Sélections gagnantes : {summary.total_won}",
            f"Sélections perdantes : {summary.total_lost}",
        ]
    )
    return "\n".join(lines)
