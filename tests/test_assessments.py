from __future__ import annotations

import polars as pl

from edutrace.simulation.assessment_models import score_attempt
from edutrace.utils.random_state import RandomStateManager


def test_score_model_bounds():
    # ``row_rng`` requires a valid table name. We use "assessment_attempt"
    # (the table whose generation actually calls ``score_attempt``) so the
    # test exercises a real RNG stream rather than a synthetic one.
    rng = RandomStateManager(seed=1).row_rng("assessment_attempt", 0)
    for _ in range(50):
        s = score_attempt(
            preparedness=0.5,
            engagement=0.5,
            item_difficulty=0.5,
            prior_attempts=0,
            maximum_score=100.0,
            rng=rng,
        )
        assert 0.0 <= s <= 100.0


def test_attempt_scores_within_max(tiny_tables):
    att = tiny_tables["assessment_attempt"]
    if att.height == 0:
        return
    assert (att["score"] <= att["maximum_score"] + 1e-9).all()


def test_attempt_numbers_positive(tiny_tables):
    att = tiny_tables["assessment_attempt"]
    if att.height == 0:
        return
    assert (att["attempt_number"] >= 1).all()


def test_item_weights_normalised(tiny_tables):
    items = tiny_tables["assessment_item"]
    sums = items.group_by("module_id").agg(pl.col("weight").sum().alias("total"))
    assert (sums["total"] - 1.0).abs().max() < 1e-6
