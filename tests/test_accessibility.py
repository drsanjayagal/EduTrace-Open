from __future__ import annotations


def test_access_reliability_bounded(tiny_tables):
    acc = tiny_tables["digital_access"]
    if acc.height == 0:
        return
    assert acc["access_reliability"].min() >= 0.0
    assert acc["access_reliability"].max() <= 1.0


def test_constraint_level_values(tiny_tables):
    acc = tiny_tables["digital_access"]
    if acc.height == 0:
        return
    allowed = {"none", "mild", "moderate", "severe"}
    assert set(acc["access_constraint_level"].unique().to_list()).issubset(allowed)


def test_one_row_per_learner_year(tiny_tables, tiny_config):
    acc = tiny_tables["digital_access"]
    if acc.height == 0:
        return
    grouped = acc.group_by(["learner_id", "observation_period"]).len()
    assert grouped["len"].max() == 1


def test_offline_usage_bounded(tiny_tables):
    acc = tiny_tables["digital_access"]
    if acc.height == 0:
        return
    assert acc["offline_access_usage"].min() >= 0.0
    assert acc["offline_access_usage"].max() <= 1.0
