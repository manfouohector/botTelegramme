"""xG Engine — estimation calibrée ou indisponible explicitement."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.repositories.match_history_repository import MatchHistoryRepository
from app.repositories.xg_data_repository import XGDataRepository
from app.utils.logging import get_logger, log_event
from app.xg.constants import MODEL_SHOT_PROXY, MODEL_UNAVAILABLE, PROXY_MODEL_VERSION
from app.xg.exceptions import InsufficientXGDataError, MatchNotFoundError
from app.xg.proxy_model import ShotProxyModel, build_training_samples
from app.xg.schemas import MatchXG
from app.xg.shot_stats import average_shot_stats, records_with_shot_data

logger = get_logger(__name__)

LIMITATION_NOTE = (
    "Proxy basé sur tirs/tirs cadrés (Sportmonks type_42/49). "
    "Ce n'est PAS un xG shot-level (xGFixture premium). "
    "Modèle Poisson calibré sur la saison."
)


class XGEngine:
    """
    Estime home_xg / away_xg pour un match.

    - Si données tirs suffisantes : proxy Poisson calibré (SHOT_PROXY_POISSON)
    - Sinon : UNAVAILABLE (pas de formule arbitraire inventée)
    """

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.history = MatchHistoryRepository(session)
        self.xg_data = XGDataRepository(session)

    def build_xg(self, match_id: int, *, as_of: datetime | None = None) -> MatchXG:
        match = self.history.get_match_by_id(match_id)
        if match is None:
            raise MatchNotFoundError(f"Match {match_id} introuvable")

        reference = self._ensure_aware(as_of or match.scheduled_at)
        if reference > self._ensure_aware(match.scheduled_at):
            raise InsufficientXGDataError("as_of postérieur à scheduled_at (data leakage)")

        if not self.settings.xg_enable_shot_proxy:
            return self._unavailable(match, reason="XG_ENABLE_SHOT_PROXY=false")

        training_records = self.xg_data.get_season_training_records(
            match.season_id,
            reference,
            competition_id=match.competition_id,
        )
        shot_records = records_with_shot_data(training_records)

        if len(shot_records) < self.settings.xg_min_training_samples:
            return self._unavailable(
                match,
                reason=f"Échantillons insuffisants ({len(shot_records)}/{self.settings.xg_min_training_samples})",
                metadata={"training_samples": len(shot_records)},
            )

        model = ShotProxyModel()
        metrics = model.fit(build_training_samples(shot_records))

        window = self.settings.xg_form_window
        home_records = self.history.get_team_finished_matches(
            match.home_team_id, reference,
            season_id=match.season_id, limit=window, venue="home",
        )
        away_records = self.history.get_team_finished_matches(
            match.away_team_id, reference,
            season_id=match.season_id, limit=window, venue="away",
        )

        home_shots = average_shot_stats(home_records)
        away_shots = average_shot_stats(away_records)

        if not home_shots.has_data or not away_shots.has_data:
            return self._unavailable(
                match,
                reason="Statistiques tirs manquantes pour les équipes",
                metadata={"home_has_shots": home_shots.has_data, "away_has_shots": away_shots.has_data},
            )

        if len(records_with_shot_data(home_records)) < self.settings.xg_min_matches:
            return self._unavailable(match, reason="Historique domicile insuffisant")
        if len(records_with_shot_data(away_records)) < self.settings.xg_min_matches:
            return self._unavailable(match, reason="Historique extérieur insuffisant")

        home_xg = model.predict(home_shots, is_home=True)
        away_xg = model.predict(away_shots, is_home=False)

        if home_xg is None or away_xg is None:
            return self._unavailable(match, reason="Prédiction proxy échouée")

        home_xg_form = self._compute_xg_form(home_records, model, is_home=True)
        away_xg_form = self._compute_xg_form(away_records, model, is_home=False)

        data_quality = self._assess_quality(
            len(records_with_shot_data(home_records)),
            len(records_with_shot_data(away_records)),
        )

        result = MatchXG(
            match_id=match.id,
            external_match_id=match.external_match_id,
            home_xg=home_xg,
            away_xg=away_xg,
            xg_difference=home_xg - away_xg,
            home_xg_form=home_xg_form,
            away_xg_form=away_xg_form,
            model_type=MODEL_SHOT_PROXY,
            model_version=PROXY_MODEL_VERSION,
            data_quality=data_quality,
            is_true_xg=False,
            metadata={
                "limitation": LIMITATION_NOTE,
                "training_metrics": metrics.to_dict(),
                "training_samples": metrics.sample_size,
            },
        )

        log_event(
            logger,
            "XG_BUILT",
            match_id=match.id,
            model_type=MODEL_SHOT_PROXY,
            home_xg=round(home_xg, 3),
            away_xg=round(away_xg, 3),
            data_quality=data_quality,
        )
        return result

    def _compute_xg_form(
        self,
        records: list,
        model: ShotProxyModel,
        *,
        is_home: bool,
    ) -> float | None:
        shot_recs = records_with_shot_data(records)
        if not shot_recs:
            return None
        preds = []
        for rec in shot_recs:
            ss = average_shot_stats([rec])
            pred = model.predict(ss, is_home=is_home)
            if pred is not None:
                preds.append(pred)
        return sum(preds) / len(preds) if preds else None

    def _unavailable(self, match, reason: str, metadata: dict | None = None) -> MatchXG:
        meta = {"limitation": LIMITATION_NOTE, "reason": reason}
        if metadata:
            meta.update(metadata)
        log_event(logger, "XG_UNAVAILABLE", level="WARNING", match_id=match.id, reason=reason)
        return MatchXG(
            match_id=match.id,
            external_match_id=match.external_match_id,
            home_xg=None,
            away_xg=None,
            xg_difference=None,
            home_xg_form=None,
            away_xg_form=None,
            model_type=MODEL_UNAVAILABLE,
            model_version=PROXY_MODEL_VERSION,
            data_quality="LOW",
            is_true_xg=False,
            metadata=meta,
        )

    def _assess_quality(self, home_n: int, away_n: int) -> str:
        minimum = self.settings.xg_min_matches
        if home_n >= minimum and away_n >= minimum:
            return "HIGH"
        if home_n >= 1 and away_n >= 1:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
