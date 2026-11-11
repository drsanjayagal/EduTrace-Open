"""Temporal integrity checks.

These test invariants the simulation is supposed to hold. A failure means
a generator has a bug, not that the model is unrealistic.
"""

from __future__ import annotations

import polars as pl

from edutrace.validation._report import CheckResult


def run_temporal_checks(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    results: list[CheckResult] = []
    results.extend(_check_events_within_enrolment_window(tables))
    results.extend(_check_feedback_after_attempt(tables))
    results.extend(_check_attempt_after_enrolment(tables))
    results.extend(_check_progression_chronological(tables))
    results.extend(_check_durations_non_negative(tables))
    results.extend(_check_weekly_week_start_aligns(tables))
    return results


def _check_events_within_enrolment_window(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    name = "temporal.event_within_enrolment"
    if "learning_event" not in tables or "enrolment" not in tables:
        return [CheckResult(name=name, status="skip", message="Missing table")]
    events = tables["learning_event"]
    enrs = tables["enrolment"].select("enrolment_id", "enrolment_date")

    joined = events.select(
        "event_id", "enrolment_id", "event_timestamp"
    ).join(enrs, on="enrolment_id", how="inner")

    before = joined.filter(
        pl.col("event_timestamp").dt.date()
        < (pl.col("enrolment_date").dt.date() - pl.duration(days=1))
    )
    n = before.height
    if n > 0:
        return [
            CheckResult(
                name=name,
                status="fail",
                message=f"{n} event(s) precede enrolment date by >1 day",
                details={"count": n},
            )
        ]
    return [CheckResult(name=name, status="pass", message="Events within windows")]


def _check_feedback_after_attempt(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    name = "temporal.feedback_after_attempt"
    if "feedback_event" not in tables or "assessment_attempt" not in tables:
        return [CheckResult(name=name, status="skip", message="Missing table")]
    fb = tables["feedback_event"].select(
        "feedback_id", "attempt_id", "feedback_timestamp"
    )
    att = tables["assessment_attempt"].select(
        "attempt_id", "attempt_timestamp"
    )
    joined = fb.join(att, on="attempt_id", how="inner")
    bad = joined.filter(pl.col("feedback_timestamp") < pl.col("attempt_timestamp"))
    if bad.height > 0:
        return [
            CheckResult(
                name=name,
                status="fail",
                message=f"{bad.height} feedback row(s) precede their attempt",
                details={"count": bad.height},
            )
        ]
    return [CheckResult(name=name, status="pass", message="Feedback after attempts")]


def _check_attempt_after_enrolment(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    name = "temporal.attempt_after_enrolment"
    if "assessment_attempt" not in tables or "enrolment" not in tables:
        return [CheckResult(name=name, status="skip", message="Missing table")]
    att = tables["assessment_attempt"].select(
        "attempt_id", "enrolment_id", "attempt_timestamp"
    )
    enrs = tables["enrolment"].select("enrolment_id", "enrolment_date")
    joined = att.join(enrs, on="enrolment_id", how="inner")
    bad = joined.filter(pl.col("attempt_timestamp") < pl.col("enrolment_date"))
    if bad.height > 0:
        return [
            CheckResult(
                name=name,
                status="fail",
                message=f"{bad.height} attempt(s) precede enrolment date",
                details={"count": bad.height},
            )
        ]
    return [CheckResult(name=name, status="pass", message="Attempts after enrolment")]


def _check_progression_chronological(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    name = "temporal.progression_chronological"
    if "progression_event" not in tables:
        return [CheckResult(name=name, status="skip", message="Missing table")]

    prog = tables["progression_event"].sort(
        ["learner_id", "semester_number", "event_timestamp"]
    ).with_columns(
        pl.col("semester_number").cum_max().over("learner_id").alias("_max_sem_so_far")
    )
    bad = prog.filter(pl.col("semester_number") < pl.col("_max_sem_so_far"))
    if bad.height > 0:
        return [
            CheckResult(
                name=name,
                status="fail",
                message=f"{bad.height} progression row(s) go backwards in semester",
                details={"count": int(bad.height)},
            )
        ]
    return [CheckResult(name=name, status="pass", message="Progression chronological")]


def _check_durations_non_negative(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    name = "temporal.durations_non_negative"
    problems: list[str] = []

    if "learning_event" in tables:
        df = tables["learning_event"]
        n = int((df["event_duration_seconds"] < 0).sum())
        if n > 0:
            problems.append(f"learning_event: {n} negative durations")

    if "assessment_attempt" in tables:
        df = tables["assessment_attempt"]
        n = int((df["duration_seconds"] < 0).sum())
        if n > 0:
            problems.append(f"assessment_attempt: {n} negative durations")

    if problems:
        return [CheckResult(name=name, status="fail", message="; ".join(problems))]
    return [CheckResult(name=name, status="pass", message="Durations non-negative")]


def _check_weekly_week_start_aligns(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    name = "temporal.weekly_week_start_aligns"
    if "weekly_engagement" not in tables:
        return [CheckResult(name=name, status="skip", message="Missing table")]
    df = tables["weekly_engagement"]
    bad = df.filter(pl.col("week_start_date").dt.weekday() != 1)
    if bad.height > 0:
        return [
            CheckResult(
                name=name,
                status="fail",
                message=f"{bad.height} weekly rows are not Monday-aligned",
                details={"count": bad.height},
            )
        ]
    return [CheckResult(name=name, status="pass", message="Week starts align")]
