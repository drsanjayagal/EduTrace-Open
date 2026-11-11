"""Cross-table consistency checks."""

from __future__ import annotations

import polars as pl

from edutrace.constants import CompletionStatus
from edutrace.simulation.dependency_models import compute_module_violations
from edutrace.validation._report import CheckResult


def run_consistency_checks(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    results: list[CheckResult] = []
    results.extend(_check_progression_credits(tables))
    results.extend(_check_weekly_minutes(tables))
    results.extend(_check_module_dependencies(tables))
    return results


def _check_progression_credits(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    name = "consistency.progression_credits"
    required = {"progression_event", "enrolment", "course"}
    if not required.issubset(tables.keys()):
        return [CheckResult(name=name, status="skip", message="Missing table")]

    prog = tables["progression_event"]
    enrs = tables["enrolment"]
    courses = tables["course"].select("course_id", "credit_value")

    # Enrolment-side totals per learner.
    enriched = enrs.join(courses, on="course_id", how="left")
    enriched = enriched.with_columns(
        pl.when(pl.col("enrolment_status") == "withdrawn")
        .then(0)
        .otherwise(pl.col("credit_value"))
        .alias("_attempted"),
        pl.when(
            (pl.col("completion_status") == CompletionStatus.COMPLETED.value)
            & (pl.col("enrolment_status") != "withdrawn")
        )
        .then(pl.col("credit_value"))
        .otherwise(0)
        .alias("_earned"),
    )
    enr_totals = enriched.group_by("learner_id").agg(
        pl.col("_attempted").sum().alias("expected_attempted"),
        pl.col("_earned").sum().alias("expected_earned"),
    )

    # Progression-side: take the learner's LAST (max semester_number) row,
    # which now holds cumulative totals.
    prog_last = (
        prog.sort(["learner_id", "semester_number"])
        .group_by("learner_id", maintain_order=True)
        .agg(
            pl.col("credits_attempted").last().alias("reported_attempted"),
            pl.col("credits_earned").last().alias("reported_earned"),
        )
    )

    joined = prog_last.join(enr_totals, on="learner_id", how="inner")
    bad = joined.filter(
        (pl.col("reported_attempted") != pl.col("expected_attempted"))
        | (pl.col("reported_earned") != pl.col("expected_earned"))
    )
    if bad.height > 0:
        return [
            CheckResult(
                name=name,
                status="fail",
                message=(
                    f"{bad.height} learner(s) whose progression credits do "
                    "not match enrolment-derived totals"
                ),
                details={"count": int(bad.height)},
            )
        ]
    return [
        CheckResult(
            name=name,
            status="pass",
            message="Progression credits consistent with enrolments",
        )
    ]


def _check_weekly_minutes(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    name = "consistency.weekly_minutes"
    required = {"weekly_engagement", "learning_event", "enrolment"}
    if not required.issubset(tables.keys()):
        return [CheckResult(name=name, status="skip", message="Missing table")]

    events = tables["learning_event"].select(
        "learner_id", "course_id", "event_duration_seconds", "event_timestamp"
    )
    enrs = tables["enrolment"].select(
        "learner_id", "course_id", "enrolment_date"
    ).unique(subset=["learner_id", "course_id"])
    joined = events.join(enrs, on=["learner_id", "course_id"], how="inner")
    joined = joined.with_columns(
        (
            (pl.col("event_timestamp").dt.date() - pl.col("enrolment_date").dt.date())
            .dt.total_days()
            // 7
            + 1
        ).clip(1, 30).alias("academic_week")
    )
    agg = joined.group_by(["learner_id", "course_id", "academic_week"]).agg(
        (pl.col("event_duration_seconds").sum() / 60.0).alias("_expected_minutes")
    )

    weekly = tables["weekly_engagement"].select(
        "learner_id", "course_id", "academic_week", "total_learning_minutes"
    )
    joined = weekly.join(
        agg, on=["learner_id", "course_id", "academic_week"], how="left"
    ).fill_null(0.0)
    diff = (joined["total_learning_minutes"] - joined["_expected_minutes"]).abs()
    bad = int((diff > 0.01).sum())
    if bad > 0:
        return [
            CheckResult(
                name=name,
                status="fail",
                message=f"{bad} weekly rows have total_learning_minutes drift >0.01",
                details={"count": bad},
            )
        ]
    return [
        CheckResult(
            name=name,
            status="pass",
            message="Weekly minutes consistent with events",
        )
    ]


def _check_module_dependencies(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    name = "consistency.module_dependencies"
    required = {"learning_event", "curriculum_dependency"}
    if not required.issubset(tables.keys()):
        return [CheckResult(name=name, status="skip", message="Missing table")]

    violations = compute_module_violations(
        tables["learning_event"], tables["curriculum_dependency"]
    )
    if violations.height > 0:
        return [
            CheckResult(
                name=name,
                status="pass",
                message=(
                    f"{violations.height} module-dependency violations recorded "
                    "(informational; simulated learners may open modules out of order)"
                ),
                severity="info",
                details={"count": int(violations.height)},
            )
        ]
    return [
        CheckResult(
            name=name,
            status="pass",
            message="No module-dependency violations",
            severity="info",
        )
    ]
