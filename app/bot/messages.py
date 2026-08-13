"""Textes des commandes utilisateur."""

from __future__ import annotations

from app.config.settings import Settings


def start_message(settings: Settings) -> str:
    return (
        f"🏟 **{settings.app_name}**\n\n"
        "Prédictions football basées sur statistiques, modèles IA et analyse "
        "des cotes bookmakers.\n\n"
        "**Fonctionnement**\n"
        "1. Analyse quotidienne des matchs\n"
        "2. Filtrage qualité (value + risque)\n"
        "3. Publication de coupons sélectionnés\n\n"
        "**Canal gratuit** — vitrine avec ~3–4 sélections de confiance\n"
        "**Premium** — coupons SAFE, VALUE, HIGH ODDS et analyses complètes\n\n"
        "Choisissez une option ci-dessous :"
    )


def free_message(settings: Settings, *, channel_link: str | None) -> str:
    if channel_link:
        return (
            f"🟢 **Canal gratuit — {settings.app_name}**\n\n"
            "Rejoignez le canal pour recevoir le coupon vitrine du jour "
            "(environ 3 à 4 sélections).\n\n"
            f"👉 {channel_link}"
        )
    return (
        f"🟢 **Canal gratuit — {settings.app_name}**\n\n"
        "Le canal gratuit n'est pas encore configuré.\n"
        "Revenez bientôt ou contactez l'administrateur."
    )


def premium_message(
    settings: Settings,
    *,
    whatsapp_link: str | None,
    premium_active: bool = False,
    premium_until: str | None = None,
) -> str:
    price = settings.premium_price.strip() or "—"
    mobile = settings.mobile_money_number.strip() or "—"
    duration = settings.premium_duration_days

    if premium_active and premium_until:
        lines = [
            f"👑 **Premium actif — {settings.app_name}**",
            "",
            f"Votre abonnement est valide jusqu'au **{premium_until}**.",
            "Rejoignez le groupe Premium si ce n'est pas déjà fait.",
        ]
        return "\n".join(lines)

    lines = [
        f"👑 **Premium — {settings.app_name}**",
        "",
        f"💰 **Prix** : {price}",
        f"📅 **Durée** : {duration} jours",
        "",
        "**Avantages Premium**",
        "• Coupons SAFE, VALUE et HIGH ODDS (si disponibles)",
        "• Plus de sélections et analyses détaillées",
        "• Probabilités, cotes, contexte et niveau de confiance",
        "• Mises à jour finales avant les matchs",
        "",
        "**Paiement V1 — Mobile Money**",
        f"Numéro : `{mobile}`",
        "",
        "Après paiement, envoyez la preuve via WhatsApp pour activation manuelle.",
    ]

    if whatsapp_link:
        lines.extend(["", f"📲 WhatsApp : {whatsapp_link}"])
    else:
        lines.extend(["", "📲 WhatsApp : non configuré pour le moment."])

    return "\n".join(lines)


def unknown_command_message() -> str:
    return (
        "Commande non reconnue.\n\n"
        "Commandes disponibles :\n"
        "/start — accueil\n"
        "/free — canal gratuit\n"
        "/premium — offre Premium\n"
        "/ping — test bot"
    )


def non_command_hint() -> str:
    return (
        "Utilisez /start pour commencer.\n"
        "Autres commandes : /free, /premium, /ping"
    )
