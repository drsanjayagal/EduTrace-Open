"""Weekly-engagement table generator.

Wraps :func:`edutrace.simulation.engagement_models.aggregate_weekly_engagement`
and adds:

1. A **Monday-aligned** ``week_start_date`` computed as the Monday on or
   before ``enrolment_date + 7*(academic_week - 1)``. This is guaranteed
   Monday-aligned regardless of what day the academic calendar starts on.
2. **Dropping** weekly rows whose ``week_start_date`` is after the
   enrolment's ``completion_date`` (when it is set), so we never emit
   "future" weekly rows.
3. **Deterministic ID assignment**: rows are sorted by (learner_id,
   course_id, academic_week) before IDs are assigned, so the same logical
   data always gets the same weekly_record_id across runs.
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.simulation.engagement_models import aggregate_weekly_engagement
from edutrace.utils.ids import PREFIX_WEEKLY, format_ids
from edutrace.utils.random_state import RandomStateManager


def _monday_on_or_before(d: date) -> date:
    """Return the Monday on or before ``d``."""
    # weekday(): Monday=0, Sunday=6.
    return d - timedelta(days=d.weekday())


def generate_weekly_engagement(
    config: EduTraceConfig,
    rng: RandomStateManager,
    events: pl.DataFrame,
    enrolments: pl.DataFrame,
    *,
    weekly_record_id_start: int = 1,
) -> tuple[pl.DataFrame, int]:
    """Return ``(weekly_df, next_weekly_record_id_start)``."""
    _ = rng  # no stochastic draws

    aggregated = aggregate_weekly_engagement(
        events,
        enrolments,
        mean_events_per_learner_week=(
            config.generation.mean_events_per_learner_week
        ),
    )
    if aggregated.is_empty():
        return _empty(), weekly_record_id_start

    enr_lookup = enrolments.select(
        "learner_id",
        "course_id",
        "enrolment_date",
        "completion_date",
    )

    joined = aggregated.join(
        enr_lookup, on=["learner_id", "course_id"], how="left"
    )

    # Compute week_start_date = Monday-on-or-before(enrolment_date + 7*(w-1)).
    # We build this in Python because date arithmetic with the Monday
    # rounding is clearer than a Polars expression.
    week_start_values: list[date | None] = []
    for row in joined.select(
        "enrolment_date", "academic_week"
    ).iter_rows(named=True):
        enrol_date = row["enrolment_date"]
        week = row["academic_week"]
        if enrol_date is None:
            week_start_values.append(None)
            continue
        # Polars returns datetime.datetime for Datetime("us"); convert to date.
        base = enrol_date.date() if hasattr(enrol_date, "date") else enrol_date
        raw = base + timedelta(days=(int(week) - 1) * 7)
        week_start_values.append(_monday_on_or_before(raw))

    joined = joined.with_columns(
        pl.Series(
            "week_start_date",
            [
                None
                if d is None
                else pl.Series([d]).cast(pl.Datetime("us"))[0]
                for d in week_start_values
            ],
            dtype=pl.Datetime("us"),
        )
    )

    # Drop rows with null week_start_date (should not happen for real data).
    joined = joined.filter(pl.col("week_start_date").is_not_null())

    # Drop rows that fall strictly after the completion date.
    joined = joined.filter(
        pl.col("completion_date").is_null()
        | (pl.col("week_start_date") <= pl.col("completion_date"))
    )

    # Deterministic row order before ID assignment.
    joined = joined.sort(["learner_id", "course_id", "academic_week"])

    n = joined.height
    ids = format_ids(
        PREFIX_WEEKLY,
        list(range(weekly_record_id_start, weekly_record_id_start + n)),
    )
    joined = joined.with_columns(pl.Series("weekly_record_id", ids))

    out = joined.select(
        "weekly_record_id",
        "learner_id",
        "course_id",
        "academic_week",
        "week_start_date",
        "login_count",
        "active_days",
        "resource_access_count",
        "total_learning_minutes",
        "assessment_attempt_count",
        "discussion_activity_count",
        "engagement_score",
        "trajectory_state",
    ).with_columns(pl.col("week_start_date").cast(pl.Datetime("us")))

    return out, weekly_record_id_start + n


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "weekly_record_id": pl.Utf8,
            "learner_id": pl.Utf8,
            "course_id": pl.Utf8,
            "academic_week": pl.Int64,
            "week_start_date": pl.Datetime("us"),
            "login_count": pl.Int64,
            "active_days": pl.Int64,
            "resource_access_count": pl.Int64,
            "total_learning_minutes": pl.Float64,
            "assessment_attempt_count": pl.Int64,
            "discussion_activity_count": pl.Int64,
            "engagement_score": pl.Float64,
            "trajectory_state": pl.Utf8,
        }
    )
