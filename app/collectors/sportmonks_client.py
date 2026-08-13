"""Client HTTP pour l'API Sportmonks v3."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx

from app.collectors.exceptions import (
    SportmonksAPIError,
    SportmonksAuthError,
    SportmonksEmptyResponseError,
    SportmonksRateLimitError,
    SportmonksTimeoutError,
)
from app.config.settings import Settings, get_settings
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)

DEFAULT_FIXTURE_INCLUDES = "participants;league;season;scores;statistics"


class SportmonksClient:
    """Client bas niveau pour Sportmonks Football API v3."""

    def __init__(self, settings: Settings | None = None, http_client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            timeout=self.settings.sportmonks_request_timeout,
            headers={"Accept": "application/json"},
        )
        self.request_count = 0

    @property
    def base_url(self) -> str:
        return self.settings.sportmonks_base_url.rstrip("/")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> SportmonksClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _build_params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        params = {"api_token": self.settings.sportmonks_api_token}
        if extra:
            params.update(extra)
        return params

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.settings.has_sportmonks():
            raise SportmonksAuthError("SPORTMONKS_API_TOKEN non configuré")

        url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        query = self._build_params(params)

        try:
            response = self._client.request(method, url, params=query)
            self.request_count += 1
        except httpx.TimeoutException as exc:
            raise SportmonksTimeoutError(f"Timeout Sportmonks : {url}") from exc
        except httpx.HTTPError as exc:
            raise SportmonksAPIError(f"Erreur HTTP Sportmonks : {exc}") from exc

        if response.status_code in (401, 403):
            raise SportmonksAuthError(
                "Authentification Sportmonks échouée",
                status_code=response.status_code,
            )
        if response.status_code == 429:
            raise SportmonksRateLimitError(
                "Quota Sportmonks dépassé",
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise SportmonksAPIError(
                f"Erreur Sportmonks HTTP {response.status_code}",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise SportmonksEmptyResponseError("Réponse JSON invalide de Sportmonks") from exc

        if not isinstance(payload, dict):
            raise SportmonksEmptyResponseError("Réponse Sportmonks inattendue (non-dict)")

        if "data" not in payload:
            message = payload.get("message", "Champ 'data' absent de la réponse")
            raise SportmonksEmptyResponseError(str(message), payload=payload)

        return payload

    @staticmethod
    def _extract_pagination(payload: dict[str, Any]) -> dict[str, Any]:
        pagination = payload.get("pagination")
        if isinstance(pagination, dict):
            return pagination
        meta = payload.get("meta")
        if isinstance(meta, dict) and isinstance(meta.get("pagination"), dict):
            return meta["pagination"]
        return {}

    def _paginate(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Récupère toutes les pages d'un endpoint paginé."""
        all_items: list[dict[str, Any]] = []
        page = 1
        params = dict(params or {})
        params.setdefault("per_page", self.settings.sportmonks_per_page)

        while True:
            params["page"] = page
            payload = self._request("GET", path, params)
            data = payload.get("data") or []

            if isinstance(data, dict):
                all_items.append(data)
                break

            if isinstance(data, list):
                all_items.extend(item for item in data if isinstance(item, dict))

            pagination = self._extract_pagination(payload)
            has_more = pagination.get("has_more", False)
            if not has_more:
                break
            page += 1

        return all_items

    def get_fixtures_by_date(
        self,
        date_str: str,
        *,
        includes: str = DEFAULT_FIXTURE_INCLUDES,
        league_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """GET /fixtures/date/{YYYY-MM-DD}"""
        params: dict[str, Any] = {"include": includes}
        if league_ids:
            params["filters"] = f"fixtureLeagues:{','.join(str(i) for i in league_ids)}"

        log_event(logger, "SPORTMONKS_FETCH_BY_DATE", date=date_str, leagues=league_ids or "all")
        return self._paginate(f"fixtures/date/{date_str}", params)

    def get_fixture_by_id(
        self,
        fixture_id: int,
        *,
        includes: str = DEFAULT_FIXTURE_INCLUDES,
    ) -> dict[str, Any]:
        """GET /fixtures/{id}"""
        payload = self._request(
            "GET",
            f"fixtures/{fixture_id}",
            {"include": includes},
        )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise SportmonksEmptyResponseError(f"Fixture {fixture_id} introuvable")
        return data

    def get_fixtures_between(
        self,
        start_date: str,
        end_date: str,
        *,
        includes: str = DEFAULT_FIXTURE_INCLUDES,
        league_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """GET /fixtures/between/{start}/{end}"""
        params: dict[str, Any] = {"include": includes}
        if league_ids:
            params["filters"] = f"fixtureLeagues:{','.join(str(i) for i in league_ids)}"

        log_event(logger, "SPORTMONKS_FETCH_BETWEEN", start=start_date, end=end_date)
        return self._paginate(f"fixtures/between/{start_date}/{end_date}", params)
