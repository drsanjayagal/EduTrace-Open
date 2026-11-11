from __future__ import annotations

from edutrace.simulation.behavioural_models import (
    classify_trajectory,
    weekly_engagement_scalar,
)


def test_trajectory_classifications():
    assert classify_trajectory(0.80) == "thriving"
    assert classify_trajectory(0.50) == "steady"
    assert classify_trajectory(0.20) == "at_risk"
    assert classify_trajectory(0.05) == "disengaged"


def test_weekly_engagement_scalar_bounded():
    for count in (0, 5, 100, 10_000):
        v = weekly_engagement_scalar(count, mean_events_per_learner_week=12.0)
        assert 0.0 <= v <= 1.0


def test_weekly_engagement_row_shape(tiny_tables):
    weekly = tiny_tables["weekly_engagement"]
    if weekly.height == 0:
        return
    assert weekly["engagement_score"].min() >= 0.0
    assert weekly["engagement_score"].max() <= 1.0
    assert weekly["active_days"].max() <= 7


def test_trajectory_state_values_in_enum(tiny_tables):
    weekly = tiny_tables["weekly_engagement"]
    if weekly.height == 0:
        return
    allowed = {"thriving", "steady", "at_risk", "disengaged"}
    assert set(weekly["trajectory_state"].unique().to_list()).issubset(allowed)
