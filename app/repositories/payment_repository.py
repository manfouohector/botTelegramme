"""Persistance paiements."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.enums import PaymentMethod, PaymentStatus
from app.models.payment import Payment


class PaymentRepository:
    """Accès PostgreSQL pour paiements."""

    def __init__(self, session: Session):
        self.session = session

    def record_success(
        self,
        user_id: int,
        *,
        amount: Decimal,
        currency: str = "XAF",
        method: PaymentMethod = PaymentMethod.MANUEL_WHATSAPP,
        reference: str | None = None,
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            method=method,
            payment_status=PaymentStatus.SUCCESS,
            reference_transaction=reference,
        )
        self.session.add(payment)
        self.session.flush()
        return payment
