"""Repository — suivi usage API (cache PostgreSQL)."""

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system import ApiUsage


class ApiUsageRepository:
    """Persiste et met à jour les compteurs d'appels API."""

    PROVIDER_SPORTMONKS = "sportmonks"
    PROVIDER_ODDS_API = "odds_api"

    def __init__(self, session: Session):
        self.session = session

    def increment(self, provider: str, count: int = 1) -> ApiUsage:
        today = date.today()
        usage = self.session.scalar(
            select(ApiUsage).where(ApiUsage.provider == provider, ApiUsage.date == today)
        )
        if usage is None:
            usage = ApiUsage(provider=provider, date=today, request_count=count)
            self.session.add(usage)
        else:
            usage.request_count += count
        usage.last_request_at = datetime.now(timezone.utc)
        self.session.flush()
        return usage

    def get_today_count(self, provider: str) -> int:
        today = date.today()
        usage = self.session.scalar(
            select(ApiUsage).where(ApiUsage.provider == provider, ApiUsage.date == today)
        )
        return usage.request_count if usage else 0
