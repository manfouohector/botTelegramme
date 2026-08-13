"""Client HTTP The Odds API v4."""

from __future__ import annotations

from typing import Any

import httpx

from app.config.settings import Settings, get_settings
from app.utils.logging import get_logger, log_event
from app.value.exceptions import OddsAPIError, OddsAuthError, OddsRateLimitError

logger = get_logger(__name__)


class OddsAPIClient:
    """Client bas niveau pour The Odds API v4."""

    def __init__(self, settings: Settings | None = None, http_client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            timeout=self.settings.odds_api_request_timeout,
            headers={"Accept": "application/json"},
        )
        self.request_count = 0

    @property
    def base_url(self) -> str:
        return self.settings.odds_api_base_url.rstrip("/")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> OddsAPIClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_sports(self) -> list[dict[str, Any]]:
        """Liste des sports disponibles."""
        return self._request("GET", "/sports")

    def get_odds_for_sport(
        self,
        sport_key: str,
        *,
        regions: str | None = None,
        markets: str | None = None,
        odds_format: str = "decimal",
    ) -> list[dict[str, Any]]:
        """Récupère les cotes pour un sport."""
        params = {
            "apiKey": self.settings.odds_api_key,
            "regions": regions or self.settings.odds_api_regions,
            "markets": markets or self.settings.get_odds_api_markets(),
            "oddsFormat": odds_format,
        }
        data = self._request("GET", f"/sports/{sport_key}/odds", params=params)
        if not isinstance(data, list):
            raise OddsAPIError("Réponse Odds API inattendue (liste attendue)")
        return data

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        if not self.settings.has_odds_api():
            raise OddsAuthError("ODDS_API_KEY non configuré")

        url = f"{self.base_url}{path}"
        try:
            response = self._client.request(method, url, params=params)
            self.request_count += 1
        except httpx.TimeoutException as exc:
            raise OddsAPIError(f"Timeout Odds API : {url}") from exc
        except httpx.HTTPError as exc:
            raise OddsAPIError(f"Erreur HTTP Odds API : {exc}") from exc

        if response.status_code in (401, 403):
            raise OddsAuthError(
                "Authentification Odds API échouée",
                status_code=response.status_code,
            )
        if response.status_code == 429:
            raise OddsRateLimitError(
                "Quota Odds API dépassé",
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise OddsAPIError(
                f"Odds API erreur {response.status_code}",
                status_code=response.status_code,
            )

        log_event(
            logger,
            "ODDS_API_REQUEST",
            path=path,
            status=response.status_code,
            remaining=response.headers.get("x-requests-remaining"),
        )
        return response.json()
