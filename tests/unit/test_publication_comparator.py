"""Tests unitaires — comparator publication."""

from app.coupons.schemas import GeneratedCoupon
from app.database.enums import CouponType
from app.publication.comparator import (
    coupons_unchanged,
    selection_fingerprint_from_generated,
)
from tests.fixtures.coupon_helpers import make_safe_pool


class TestPublicationComparator:
    def test_fingerprint_and_unchanged(self):
        pool_a = make_safe_pool(3, start_id=1)
        pool_b = make_safe_pool(3, start_id=1)
        pool_c = make_safe_pool(3, start_id=10)

        gen_a = GeneratedCoupon(coupon_type=CouponType.FREE, candidates=pool_a, total_odds=1.0)
        gen_b = GeneratedCoupon(coupon_type=CouponType.FREE, candidates=pool_b, total_odds=1.0)
        gen_c = GeneratedCoupon(coupon_type=CouponType.FREE, candidates=pool_c, total_odds=1.0)

        fp_a = selection_fingerprint_from_generated(gen_a)
        fp_b = selection_fingerprint_from_generated(gen_b)
        fp_c = selection_fingerprint_from_generated(gen_c)

        assert coupons_unchanged(fp_a, fp_b)
        assert not coupons_unchanged(fp_a, fp_c)
