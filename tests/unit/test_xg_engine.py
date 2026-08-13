"""Tests unitaires/intégration — XGEngine."""

import pytest

from app.config.settings import Settings
from app.xg.constants import MODEL_SHOT_PROXY, MODEL_UNAVAILABLE
from app.xg.exceptions import InsufficientXGDataError, MatchNotFoundError
from app.xg.xg_engine import XGEngine
from tests.fixtures.xg_helpers import seed_xg_test_data


class TestXGEngine:
    @pytest.fixture
    def settings(self):
        return Settings(
            _env_file=None,
            xg_form_window=5,
            xg_min_matches=3,
            xg_min_training_samples=20,
            xg_enable_shot_proxy=True,
        )

    def test_build_xg_success(self, db_session, settings):
        data = seed_xg_test_data(db_session)
        engine = XGEngine(db_session, settings)
        xg = engine.build_xg(data["target_match"].id)

        assert xg.model_type == MODEL_SHOT_PROXY
        assert xg.is_true_xg is False
        assert xg.home_xg is not None
        assert xg.away_xg is not None
        assert xg.xg_difference is not None
        assert xg.home_xg_form is not None
        assert xg.home_xg >= 0
        assert "limitation" in xg.metadata
        assert xg.data_quality in ("HIGH", "MEDIUM")

    def test_flat_features(self, db_session, settings):
        data = seed_xg_test_data(db_session)
        engine = XGEngine(db_session, settings)
        xg = engine.build_xg(data["target_match"].id)
        flat = xg.flat_features()
        assert "home_xg" in flat
        assert "xg_difference" in flat

    def test_unavailable_insufficient_training(self, db_session, settings):
        settings.xg_min_training_samples = 100
        data = seed_xg_test_data(db_session)
        engine = XGEngine(db_session, settings)
        xg = engine.build_xg(data["target_match"].id)
        assert xg.model_type == MODEL_UNAVAILABLE
        assert xg.home_xg is None

    def test_unavailable_disabled(self, db_session, settings):
        settings.xg_enable_shot_proxy = False
        data = seed_xg_test_data(db_session)
        engine = XGEngine(db_session, settings)
        xg = engine.build_xg(data["target_match"].id)
        assert xg.model_type == MODEL_UNAVAILABLE

    def test_match_not_found(self, db_session, settings):
        engine = XGEngine(db_session, settings)
        with pytest.raises(MatchNotFoundError):
            engine.build_xg(99999)

    def test_as_of_leakage(self, db_session, settings):
        from datetime import datetime, timezone

        data = seed_xg_test_data(db_session)
        engine = XGEngine(db_session, settings)
        with pytest.raises(InsufficientXGDataError):
            engine.build_xg(
                data["target_match"].id,
                as_of=datetime(2027, 1, 1, tzinfo=timezone.utc),
            )

    def test_training_metrics_present(self, db_session, settings):
        data = seed_xg_test_data(db_session)
        engine = XGEngine(db_session, settings)
        xg = engine.build_xg(data["target_match"].id)
        assert "training_metrics" in xg.metadata
        assert xg.metadata["training_metrics"]["sample_size"] >= 20

    def test_to_dict(self, db_session, settings):
        data = seed_xg_test_data(db_session)
        engine = XGEngine(db_session, settings)
        xg = engine.build_xg(data["target_match"].id)
        d = xg.to_dict()
        assert d["is_true_xg"] is False
        assert d["model_type"] == MODEL_SHOT_PROXY
