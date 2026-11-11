"""Weekly-engagement aggregation helpers.

Consumes an *already generated* learning_event table and produces weekly
aggregates per (learner, course, academic_week).

The academic week is anchored to the enrolment's start date. ``active_days``
is capped at 7 (a calendar week) so the schema bound is guaranteed even if
the elapsed day-range within a "week" bucketing is 8 due to date alignment.
"""

from __future__ import annotations

import polars as pl

from edutrace.simulation.behavioural_models import (
    classify_trajectory,
    weekly_engagement_scalar,
)


def aggregate_weekly_engagement(
    events: pl.DataFrame,
    enrolments: pl.DataFrame,
    *,
    mean_events_per_learner_week: float,
) -> pl.DataFrame:
    """Return weekly aggregate rows per (learner, course, academic_week)."""
    if events.is_empty() or enrolments.is_empty():
        return _empty()

    enr_keyed = enrolments.select(
        "learner_id", "course_id", "enrolment_id", "enrolment_date", "semester"
    )

    joined = events.join(
        enr_keyed,
        on=["learner_id", "course_id"],
        how="inner",
    )

    # Week index: floor((event_date - enrolment_date) / 7) + 1, clipped to
    # [1, 30].
    joined = joined.with_columns(
        (
            (
                (
                    pl.col("event_timestamp").dt.date()
                    - pl.col("enrolment_date").dt.date()
                ).dt.total_days()
                // 7
            )
            + 1
        ).clip(1, 30).alias("academic_week")
    )

    agg = (
        joined.group_by(["learner_id", "course_id", "academic_week"])
        .agg(
            pl.col("event_type").eq("login").sum().alias("login_count"),
            # Active days: distinct days, capped at 7 to respect the
            # schema's 0..7 bound. An 8-day calendar span can occur if the
            # enrolment date itself is mid-week; the cap is a modelling
            # decision that keeps the field semantically correct.
            pl.col("event_timestamp")
            .dt.date()
            .n_unique()
            .clip(0, 7)
            .alias("active_days"),
            pl.col("event_type")
            .is_in(
                [
                    "resource_view",
                    "resource_download",
                    "video_start",
                    "video_complete",
                ]
            )
            .sum()
            .alias("resource_access_count"),
            (pl.col("event_duration_seconds").sum() / 60.0).alias(
                "total_learning_minutes"
            ),
            pl.col("event_type")
            .is_in(["quiz_submit", "assignment_submit"])
            .sum()
            .alias("assessment_attempt_count"),
            pl.col("event_type")
            .is_in(["discussion_post", "forum_reply", "discussion_view"])
            .sum()
            .alias("discussion_activity_count"),
            pl.col("event_type").count().alias("_event_count"),
        )
    )

    score_rows: list[dict] = []
    for row in agg.iter_rows(named=True):
        score = weekly_engagement_scalar(
            row["_event_count"], mean_events_per_learner_week
        )
        score_rows.append(
            {
                "learner_id": row["learner_id"],
                "course_id": row["course_id"],
                "academic_week": row["academic_week"],
                "login_count": row["login_count"],
                "active_days": min(7, int(row["active_days"])),
                "resource_access_count": row["resource_access_count"],
                "total_learning_minutes": round(
                    row["total_learning_minutes"], 3
                ),
                "assessment_attempt_count": row["assessment_attempt_count"],
                "discussion_activity_count": row["discussion_activity_count"],
                "engagement_score": round(score, 4),
                "trajectory_state": classify_trajectory(score),
            }
        )

    if not score_rows:
        return _empty()

    return pl.from_dicts(score_rows).with_columns(
        [
            pl.col("learner_id").cast(pl.Utf8),
            pl.col("course_id").cast(pl.Utf8),
            pl.col("academic_week").cast(pl.Int64),
            pl.col("login_count").cast(pl.Int64),
            pl.col("active_days").cast(pl.Int64),
            pl.col("resource_access_count").cast(pl.Int64),
            pl.col("total_learning_minutes").cast(pl.Float64),
            pl.col("assessment_attempt_count").cast(pl.Int64),
            pl.col("discussion_activity_count").cast(pl.Int64),
            pl.col("engagement_score").cast(pl.Float64),
            pl.col("trajectory_state").cast(pl.Utf8),
        ]
    )


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "learner_id": pl.Utf8,
            "course_id": pl.Utf8,
            "academic_week": pl.Int64,
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
