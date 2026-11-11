"""Leakage validation.

Leakage means future information is used where past information is
required. The dataset doesn't itself train models; instead we check the
invariants that would make any downstream *temporal* model honest:

* Feedback timestamps are >= their attempt timestamps (no future feedback).
* Each ``progression_event`` is *semester-scoped*: for the corresponding
  semester, no enrolment has a ``completion_date`` strictly after the
  progression event's timestamp. The corresponding semester is derived
  from the learner's ``admission_year`` and the config's
  ``semesters_per_year`` (mapping the progression's within-programme
  ``semester_number`` back to the learner's ``(academic_year, semester)``
  coordinate).
* Weekly records' ``week_start_date`` is <= the enrolment's
  ``completion_date``.
"""

from __future__ import annotations

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.validation._report import CheckResult


def run_leakage_checks(
    tables: dict[str, pl.DataFrame],
    config: EduTraceConfig,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    results.extend(_check_feedback_not_future(tables))
    results.extend(_check_progression_not_future(tables, config))
    results.extend(_check_weekly_not_future(tables))
    return results


def _check_feedback_not_future(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    name = "leakage.feedback_not_future"
    if "feedback_event" not in tables or "assessment_attempt" not in tables:
        return [CheckResult(name=name, status="skip", message="Missing table")]
    fb = tables["feedback_event"].select(
        "feedback_id", "attempt_id", "feedback_timestamp"
    )
    att = tables["assessment_attempt"].select(
        "attempt_id", "attempt_timestamp"
    )
    bad = fb.join(att, on="attempt_id", how="inner").filter(
        pl.col("feedback_timestamp") < pl.col("attempt_timestamp")
    )
    if bad.height > 0:
        return [
            CheckResult(
                name=name,
                status="fail",
                message=f"{bad.height} feedback row(s) have future timestamps",
            )
        ]
    return [CheckResult(name=name, status="pass", message="Feedback is not future")]


def _check_progression_not_future(
    tables: dict[str, pl.DataFrame],
    config: EduTraceConfig,
) -> list[CheckResult]:
    """For each progression_event, verify that no *same-semester* enrolment
    has a ``completion_date`` strictly after the event's timestamp.

    The mapping from ``progression_event.semester_number`` (within-programme
    index) back to ``enrolment.(academic_year, semester)`` uses the
    learner's ``admission_year`` and the config's ``semesters_per_year`` —
    this is the same mapping ``generate_progression_events`` uses.
    """
    name = "leakage.progression_not_future"
    required = {"progression_event", "enrolment", "learner"}
    if not required.issubset(tables.keys()):
        return [CheckResult(name=name, status="skip", message="Missing table")]

    prog = tables["progression_event"].select(
        "learner_id", "semester_number", "event_timestamp"
    )
    enr = tables["enrolment"].select(
        "learner_id",
        "academic_year",
        "semester",
        "completion_date",
    ).filter(pl.col("completion_date").is_not_null())
    learners = tables["learner"].select("learner_id", "admission_year")

    semesters_per_year = config.generation.semesters_per_year
    if semesters_per_year <= 0:
        return [
            CheckResult(
                name=name,
                status="skip",
                message="Invalid semesters_per_year",
            )
        ]

    # Map semester_number → (academic_year, semester) per learner.
    joined = prog.join(learners, on="learner_id", how="inner")
    joined = joined.with_columns(
        ((pl.col("semester_number") - 1) // semesters_per_year).alias(
            "_year_offset"
        ),
        (((pl.col("semester_number") - 1) % semesters_per_year) + 1).alias(
            "_semester_within_year"
        ),
    ).with_columns(
        (pl.col("admission_year") + pl.col("_year_offset")).alias(
            "_derived_academic_year"
        ),
    )

    # Join the enrolments on (learner_id, derived_academic_year, semester).
    joined = joined.join(
        enr,
        left_on=["learner_id", "_derived_academic_year", "_semester_within_year"],
        right_on=["learner_id", "academic_year", "semester"],
        how="inner",
    )

    bad = joined.filter(pl.col("completion_date") > pl.col("event_timestamp"))
    if bad.height > 0:
        return [
            CheckResult(
                name=name,
                status="fail",
                message=(
                    f"{bad.height} (learner, semester) pair(s) have "
                    "enrolments completed after the progression event"
                ),
                details={"count": int(bad.height)},
            )
        ]
    return [
        CheckResult(name=name, status="pass", message="Progression not future")
    ]


def _check_weekly_not_future(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    name = "leakage.weekly_not_future"
    if "weekly_engagement" not in tables or "enrolment" not in tables:
        return [CheckResult(name=name, status="skip", message="Missing table")]
    weekly = tables["weekly_engagement"].select(
        "learner_id", "course_id", "week_start_date"
    )
    enr = tables["enrolment"].select(
        "learner_id", "course_id", "completion_date"
    ).filter(pl.col("completion_date").is_not_null())
    joined = weekly.join(
        enr, on=["learner_id", "course_id"], how="inner"
    )
    bad = joined.filter(pl.col("week_start_date") > pl.col("completion_date"))
    if bad.height > 0:
        return [
            CheckResult(
                name=name,
                status="fail",
                message=(
                    f"{bad.height} weekly row(s) start after their "
                    "enrolment's completion date"
                ),
            )
        ]
    return [CheckResult(name=name, status="pass", message="Weekly not future")]
