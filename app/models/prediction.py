"""Modèles IA, prédictions et résultats."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from app.database.types import JSONType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.database.enums import ConfidenceLevel


class AIModel(Base, TimestampMixin):
    __tablename__ = "ai_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSONType)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(default=False, index=True)

    features: Mapped[list["ModelFeature"]] = relationship(back_populates="model")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="model")


class ModelFeature(Base, TimestampMixin):
    __tablename__ = "model_features"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    importance: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    metadata_json: Mapped[dict | None] = mapped_column(JSONType)

    model: Mapped["AIModel"] = relationship(back_populates="features")


class Prediction(Base, TimestampMixin):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    market_id: Mapped[int] = mapped_column(
        ForeignKey("markets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    model_id: Mapped[int] = mapped_column(
        ForeignKey("ai_models.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    selection: Mapped[str] = mapped_column(String(100), nullable=False)
    probability: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    odds: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    implied_probability: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    value_edge: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    confidence: Mapped[ConfidenceLevel] = mapped_column(
        String(10), nullable=False, default=ConfidenceLevel.MEDIUM
    )
    features_snapshot: Mapped[dict | None] = mapped_column(JSONType)
    risk_decision: Mapped[str | None] = mapped_column(String(20))

    match: Mapped["Match"] = relationship(back_populates="predictions")
    market: Mapped["Market"] = relationship(back_populates="predictions")
    model: Mapped["AIModel"] = relationship(back_populates="predictions")
    result: Mapped["PredictionResult | None"] = relationship(
        back_populates="prediction", uselist=False
    )
    coupon_links: Mapped[list["CouponPrediction"]] = relationship(back_populates="prediction")


class PredictionResult(Base):
    __tablename__ = "prediction_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    actual_result: Mapped[str] = mapped_column(String(100), nullable=False)
    is_correct: Mapped[bool] = mapped_column(nullable=False)
    clv: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    settled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prediction: Mapped["Prediction"] = relationship(back_populates="result")
