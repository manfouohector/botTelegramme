"""Context Engine — calcul du contexte structuré sans LLM."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.context.calculators.factors import (
    assess_context_quality,
    build_standings_map,
    compute_context_factors,
    get_leader_points,
)
from app.context.exceptions import InsufficientStandingsError, MatchNotFoundError
from app.context.schemas import MatchContext
from app.context.standings import StandingsCalculator
from app.repositories.context_repository import ContextRepository
from app.repositories.match_history_repository import MatchHistoryRepository
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)

CUP_KEYWORDS = ("cup", "coupe", "copa", "pokal", "taça", "champions", "europa", "conference")


class ContextEngine:
    """
    Calcule le contexte d'un match à partir de données structurées.

    Le LLM n'intervient PAS ici — uniquement des faits numériques calculés.
    Anti-leakage : classement basé sur matchs FINISHED avant scheduled_at.
    """

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.history = MatchHistoryRepository(session)
        self.standings_calc = StandingsCalculator(session)
        self.context_repo = ContextRepository(session)

    def build_context(
        self,
        match_id: int,
        *,
        as_of: datetime | None = None,
        persist: bool = False,
    ) -> MatchContext:
        """Calcule le contexte complet d'un match."""
        match = self.history.get_match_by_id(match_id)
        if match is None:
            raise MatchNotFoundError(f"Match {match_id} introuvable")

        reference = self._ensure_aware(as_of or match.scheduled_at)
        if reference > self._ensure_aware(match.scheduled_at):
            raise InsufficientStandingsError(
                "as_of postérieur à scheduled_at interdit (data leakage)"
            )

        snapshot = self.standings_calc.compute(
            match.season_id,
            reference,
            competition_id=match.competition_id,
        )
        standings_map = build_standings_map(snapshot)
        leader_points = get_leader_points(snapshot)

        home_standing = standings_map.get(match.home_team_id)
        away_standing = standings_map.get(match.away_team_id)

        matches_remaining = self.standings_calc.count_remaining_matches(
            match.season_id,
            reference,
            competition_id=match.competition_id,
        )

        is_derby = self._is_derby(
            match.home_team.external_id,
            match.away_team.external_id,
        )
        is_cup = self._is_cup_match(match.competition.name if match.competition else "")

        factors = compute_context_factors(
            home_standing=home_standing,
            away_standing=away_standing,
            total_teams=snapshot.total_teams,
            matches_remaining=matches_remaining,
            is_derby=is_derby,
            is_cup=is_cup,
            settings=self.settings,
            leader_points=leader_points,
        )

        data_quality = assess_context_quality(home_standing, away_standing)

        context = MatchContext(
            match_id=match.id,
            external_match_id=match.external_match_id,
            scheduled_at=match.scheduled_at,
            as_of=reference,
            home_standing=home_standing,
            away_standing=away_standing,
            factors=factors,
            matches_remaining=matches_remaining,
            data_quality=data_quality,
            metadata={
                "total_teams": snapshot.total_teams,
                "competition_id": match.competition_id,
                "season_id": match.season_id,
            },
        )

        if persist:
            self.context_repo.save_context(context)

        log_event(
            logger,
            "CONTEXT_BUILT",
            match_id=match.id,
            data_quality=data_quality,
            high_stakes=context.get_factor("high_stakes"),
            title_race=context.get_factor("title_race"),
            relegation_battle=context.get_factor("relegation_battle"),
        )
        return context

    def build_context_batch(
        self,
        match_ids: list[int],
        *,
        persist: bool = False,
    ) -> list[MatchContext]:
        results: list[MatchContext] = []
        for mid in match_ids:
            try:
                results.append(self.build_context(mid, persist=persist))
            except (MatchNotFoundError, InsufficientStandingsError) as exc:
                log_event(logger, "CONTEXT_SKIPPED", level="WARNING", match_id=mid, reason=str(exc))
        return results

    def _is_derby(self, home_external_id: int, away_external_id: int) -> bool:
        pair = (min(home_external_id, away_external_id), max(home_external_id, away_external_id))
        return pair in self.settings.get_context_derby_pairs()

    @staticmethod
    def _is_cup_match(competition_name: str) -> bool:
        name = competition_name.lower()
        return any(kw in name for kw in CUP_KEYWORDS)

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
