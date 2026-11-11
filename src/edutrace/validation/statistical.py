"""Statistical validation: distribution summaries and degenerate-data checks."""

from __future__ import annotations

import polars as pl

from edutrace.validation._report import CheckResult

_VARIANCE_EXPECTED: dict[str, list[str]] = {
    "learner": ["baseline_preparedness", "initial_engagement_profile"],
    "enrolment": ["final_grade"],
    "learning_resource": ["difficulty_level", "estimated_duration"],
    "assessment_item": ["difficulty", "maximum_score"],
    "assessment_attempt": ["score", "duration_seconds"],
    "weekly_engagement": ["engagement_score", "login_count"],
    "digital_access": ["access_reliability"],
    "progression_event": ["credits_earned"],
}


def run_statistical_checks(
    tables: dict[str, pl.DataFrame],
    *,
    enabled: bool = True,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not enabled:
        results.append(
            CheckResult(
                name="statistical.disabled",
                status="skip",
                message="Statistical checks disabled by configuration",
            )
        )
        return results

    for table_name, df in tables.items():
        if df.is_empty():
            continue
        numeric_cols = [
            c for c, t in df.schema.items()
            if isinstance(t, (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                              pl.Float32, pl.Float64))
        ]
        for col in numeric_cols:
            series = df[col].drop_nulls()
            if series.is_empty():
                results.append(
                    CheckResult(
                        name=f"statistical.null.{table_name}.{col}",
                        status="fail",
                        message=f"{table_name}.{col}: all values are null",
                    )
                )
                continue
            # Variance check only for known-expected-variance columns.
            # Combined into one condition; identical semantics to the
            # previously nested form.
            if (
                table_name in _VARIANCE_EXPECTED
                and col in _VARIANCE_EXPECTED[table_name]
                and series.n_unique() <= 1
            ):
                results.append(
                    CheckResult(
                        name=f"statistical.variance.{table_name}.{col}",
                        status="fail",
                        message=(
                            f"{table_name}.{col}: zero variance where "
                            "variation is expected"
                        ),
                    )
                )

    counts = {t: int(df.height) for t, df in tables.items()}
    results.append(
        CheckResult(
            name="statistical.row_counts",
            status="pass",
            message="Row counts captured",
            severity="info",
            details={"counts": counts},
        )
    )
    return results
