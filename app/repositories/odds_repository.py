"""Repository — persistance et lecture des cotes."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.market import Market, Odd
from app.repositories.prediction_repository import PredictionRepository
from app.value.implied import decimal_to_implied
from app.value.schemas import NormalizedOdd


class OddsRepository:
    """Accès PostgreSQL pour les cotes bookmakers."""

    def __init__(self, session: Session):
        self.session = session
        self._markets = PredictionRepository(session)

    def store_normalized_odds(
        self,
        match_id: int,
        odds_list: list[NormalizedOdd],
        *,
        fetched_at: datetime | None = None,
    ) -> list[Odd]:
        """Persiste des cotes normalisées."""
        ts = fetched_at or datetime.now(timezone.utc)
        rows: list[Odd] = []

        for odd in odds_list:
            market = self._markets.get_or_create_market(odd.market_code, name=odd.market_code)
            implied = Decimal(str(round(decimal_to_implied(odd.decimal_odds), 6)))
            row = Odd(
                match_id=match_id,
                market_id=market.id,
                bookmaker=odd.bookmaker,
                selection=odd.selection,
                odds=Decimal(str(round(odd.decimal_odds, 4))),
                implied_probability=implied,
                fetched_at=ts,
            )
            self.session.add(row)
            rows.append(row)

        self.session.flush()
        return rows

    def get_latest_odds_for_match(self, match_id: int) -> list[Odd]:
        """Dernières cotes par (market, bookmaker, selection)."""
        latest_ts = self.session.scalar(
            select(func.max(Odd.fetched_at)).where(Odd.match_id == match_id)
        )
        if latest_ts is None:
            return []

        return list(
            self.session.scalars(
                select(Odd)
                .where(and_(Odd.match_id == match_id, Odd.fetched_at == latest_ts))
                .order_by(Odd.market_id, Odd.bookmaker, Odd.selection)
            ).all()
        )

    def get_market_odds_snapshot(
        self,
        match_id: int,
        *,
        bookmaker: str | None = None,
    ) -> dict[str, dict[str, Odd]]:
        """
        Retourne {market_code: {selection: Odd}} pour le snapshot le plus récent.

        Si bookmaker précisé, filtre ; sinon prend la cote la plus haute par sélection.
        """
        odds_rows = self.get_latest_odds_for_match(match_id)
        if not odds_rows:
            return {}

        market_ids = {row.market_id for row in odds_rows}
        markets = {
            m.id: m.code
            for m in self.session.scalars(select(Market).where(Market.id.in_(market_ids))).all()
        }

        snapshot: dict[str, dict[str, Odd]] = {}
        for row in odds_rows:
            market_code = markets.get(row.market_id)
            if not market_code:
                continue
            if bookmaker and row.bookmaker != bookmaker:
                continue

            bucket = snapshot.setdefault(market_code, {})
            existing = bucket.get(row.selection)
            if existing is None or float(row.odds) > float(existing.odds):
                bucket[row.selection] = row

        return snapshot

    def get_closing_odds(
        self,
        match_id: int,
        market_id: int,
        selection: str,
    ) -> float | None:
        """Récupère la cote de clôture si disponible."""
        row = self.session.scalar(
            select(Odd)
            .where(
                Odd.match_id == match_id,
                Odd.market_id == market_id,
                Odd.selection == selection,
            )
            .order_by(Odd.fetched_at.desc())
            .limit(1)
        )
        if row is None:
            return None
        if row.closing_odds is not None:
            return float(row.closing_odds)
        return float(row.odds)
