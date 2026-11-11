"""Learning-trajectory analyses over weekly engagement."""

from __future__ import annotations

import polars as pl


def trajectory_state_counts(weekly_engagement: pl.DataFrame) -> pl.DataFrame:
    """Counts of each trajectory_state."""
    return (
        weekly_engagement["trajectory_state"]
        .value_counts()
        .sort("count", descending=True)
    )


def mean_engagement_by_week(weekly_engagement: pl.DataFrame) -> pl.DataFrame:
    """Mean engagement_score and active_days per academic_week."""
    return (
        weekly_engagement.group_by("academic_week")
        .agg(
            pl.col("engagement_score").mean().alias("mean_engagement"),
            pl.col("active_days").mean().alias("mean_active_days"),
            pl.col("total_learning_minutes").mean().alias("mean_learning_minutes"),
            pl.len().alias("n_rows"),
        )
        .sort("academic_week")
    )


def engagement_volatility(weekly_engagement: pl.DataFrame) -> pl.DataFrame:
    """Std-dev of engagement per learner across weeks.

    Higher values indicate less stable engagement. This is a statistic;
    it is not an empirical claim about any population.
    """
    return (
        weekly_engagement.group_by("learner_id")
        .agg(
            pl.col("engagement_score").std().alias("engagement_std"),
            pl.col("engagement_score").mean().alias("engagement_mean"),
            pl.len().alias("n_weeks"),
        )
        .filter(pl.col("n_weeks") >= 2)
        .sort("engagement_std", descending=True)
    )
