"""Publication Telegram — canal gratuit + groupe Premium."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.publication.schemas import PublicationBatchResult, PublishedCouponResult

__all__ = ["PublicationBatchResult", "PublishedCouponResult"]


def __getattr__(name: str):
    if name in __all__:
        from app.publication import schemas

        return getattr(schemas, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
