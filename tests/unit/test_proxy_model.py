"""Tests unitaires — modèle proxy Poisson."""

from app.xg.proxy_model import ShotProxyModel, TrainingSample, build_training_samples
from app.features.records import TeamMatchRecord


def _sample(goals, shots, sot, is_home):
    return TrainingSample(shots=shots, shots_on_target=sot, is_home=is_home, goals=goals)


class TestShotProxyModel:
    def test_fit_and_predict(self):
        samples = [
            _sample(0, 8, 2, 1), _sample(1, 10, 4, 1), _sample(2, 14, 6, 1),
            _sample(3, 18, 8, 1), _sample(1, 11, 3, 1), _sample(0, 7, 2, 0),
            _sample(1, 9, 3, 0), _sample(2, 13, 5, 0), _sample(1, 12, 4, 0),
            _sample(0, 6, 1, 0),
        ]
        model = ShotProxyModel()
        metrics = model.fit(samples)
        assert model.trained is True
        assert metrics.sample_size == 10
        assert metrics.mean_absolute_error is not None

        from app.xg.schemas import ShotStats
        pred = model.predict(ShotStats(shots=15, shots_on_target=6), is_home=True)
        assert pred is not None
        assert pred >= 0

    def test_insufficient_samples(self):
        model = ShotProxyModel()
        metrics = model.fit([_sample(1, 10, 4, 1)])
        assert model.trained is False
        assert metrics.sample_size == 1

    def test_build_training_samples(self):
        from datetime import datetime, timezone

        rec = TeamMatchRecord(
            match_id=1, scheduled_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            team_id=1, opponent_id=2, is_home=True, goals_scored=2, goals_conceded=1,
            stats={"type_42": 14, "type_49": 6},
        )
        samples = build_training_samples([rec])
        assert len(samples) == 1
        assert samples[0].goals == 2
