"""Feature Engine — calcul de features sans data leakage."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.features.calculators import (
    compute_attack_defense_features,
    compute_form_features,
    compute_h2h_features,
    compute_home_away_features,
)
from app.features.exceptions import InsufficientDataError, MatchNotFoundError
from app.features.schemas import MatchFeatures
from app.repositories.match_history_repository import MatchHistoryRepository
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


class FeatureEngine:
    """
    Construit les features d'un match à partir de l'historique PostgreSQL.

    Anti-leakage :
    - Seuls les matchs FINISHED avec scheduled_at < match cible sont utilisés
    - as_of par défaut = scheduled_at du match cible
    - Le match cible n'est jamais inclus dans l'historique
    """

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.history = MatchHistoryRepository(session)

    def build_features(
        self,
        match_id: int,
        *,
        as_of: datetime | None = None,
    ) -> MatchFeatures:
        """Calcule toutes les features pour un match."""
        match = self.history.get_match_by_id(match_id)
        if match is None:
            raise MatchNotFoundError(f"Match {match_id} introuvable")

        reference = as_of or match.scheduled_at
        reference = self._ensure_aware(reference)

        if reference > self._ensure_aware(match.scheduled_at):
            raise InsufficientDataError(
                "as_of ne peut pas être postérieur à scheduled_at du match (data leakage)"
            )

        form_window = self.settings.feature_form_window
        h2h_window = self.settings.feature_h2h_window

        home_records = self.history.get_team_finished_matches(
            match.home_team_id,
            reference,
            season_id=match.season_id,
            limit=form_window,
        )
        away_records = self.history.get_team_finished_matches(
            match.away_team_id,
            reference,
            season_id=match.season_id,
            limit=form_window,
        )
        home_at_home = self.history.get_team_finished_matches(
            match.home_team_id,
            reference,
            season_id=match.season_id,
            limit=form_window,
            venue="home",
        )
        away_at_away = self.history.get_team_finished_matches(
            match.away_team_id,
            reference,
            season_id=match.season_id,
            limit=form_window,
            venue="away",
        )
        h2h_matches = self.history.get_h2h_matches(
            match.home_team_id,
            match.away_team_id,
            reference,
            limit=h2h_window,
        )

        home_form = compute_form_features(match.home_team_id, home_records)
        away_form = compute_form_features(match.away_team_id, away_records)
        home_venue = compute_home_away_features(match.home_team_id, home_at_home, "home")
        away_venue = compute_home_away_features(match.away_team_id, away_at_away, "away")
        home_ad = compute_attack_defense_features(home_records)
        away_ad = compute_attack_defense_features(away_records)
        h2h = compute_h2h_features(h2h_matches, match.home_team_id, match.away_team_id)

        data_quality = self._assess_quality(
            home_form.matches_played,
            away_form.matches_played,
        )

        features = MatchFeatures(
            match_id=match.id,
            external_match_id=match.external_match_id,
            home_team_id=match.home_team_id,
            away_team_id=match.away_team_id,
            scheduled_at=match.scheduled_at,
            as_of=reference,
            home_form=home_form,
            away_form=away_form,
            home_at_home=home_venue,
            away_at_away=away_venue,
            home_attack_defense=home_ad,
            away_attack_defense=away_ad,
            h2h=h2h,
            data_quality=data_quality,
            matches_used_home=home_form.matches_played,
            matches_used_away=away_form.matches_played,
            metadata={
                "form_window": form_window,
                "h2h_window": h2h_window,
                "season_id": match.season_id,
            },
        )

        log_event(
            logger,
            "FEATURES_BUILT",
            match_id=match.id,
            data_quality=data_quality,
            home_matches=home_form.matches_played,
            away_matches=away_form.matches_played,
        )
        return features

    def build_features_batch(
        self,
        match_ids: list[int],
        *,
        as_of: datetime | None = None,
        skip_insufficient: bool = True,
    ) -> list[MatchFeatures]:
        """Calcule les features pour plusieurs matchs."""
        results: list[MatchFeatures] = []
        for mid in match_ids:
            try:
                results.append(self.build_features(mid, as_of=as_of))
            except (MatchNotFoundError, InsufficientDataError) as exc:
                if not skip_insufficient:
                    raise
                log_event(logger, "FEATURES_SKIPPED", level="WARNING", match_id=mid, reason=str(exc))
        return results

    def _assess_quality(self, home_matches: int, away_matches: int) -> str:
        minimum = self.settings.feature_min_matches
        if home_matches >= minimum and away_matches >= minimum:
            return "HIGH"
        if home_matches >= 1 and away_matches >= 1:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
