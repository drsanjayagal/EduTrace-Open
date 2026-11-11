"""Module-dependency checking utilities.

The dataset does not *enforce* dependencies at generation time (learners
may open modules before prerequisites are complete). Instead it records
enough information for a downstream validator to compute violations.
This module provides the pure functions used both by the
`validation.consistency` module (Phase 8) and by analytical notebooks.

A "violation" is defined as a `module_open` or `module_complete` event whose
`module_id` has at least one *unmet* predecessor: a predecessor module for
which the learner has no `module_complete` event with an earlier timestamp.
"""

from __future__ import annotations

import polars as pl


def compute_module_violations(
    events: pl.DataFrame,
    curriculum_dependencies: pl.DataFrame,
) -> pl.DataFrame:
    """Return one row per dependency violation.

    Parameters
    ----------
    events:
        Must contain ``learner_id``, ``module_id``, ``event_timestamp``,
        ``event_type``.
    curriculum_dependencies:
        Must contain ``predecessor_module_id``, ``successor_module_id``,
        ``dependency_type``.

    The output contains: ``learner_id``, ``module_id``, ``event_timestamp``,
    ``predecessor_module_id``, ``dependency_type``.
    """
    if events.is_empty() or curriculum_dependencies.is_empty():
        return pl.DataFrame(
            schema={
                "learner_id": pl.Utf8,
                "module_id": pl.Utf8,
                "event_timestamp": pl.Datetime("us"),
                "predecessor_module_id": pl.Utf8,
                "dependency_type": pl.Utf8,
            }
        )

    # Completion times per (learner, module).
    completions = events.filter(pl.col("event_type") == "module_complete").select(
        "learner_id",
        pl.col("module_id").alias("completed_module_id"),
        pl.col("event_timestamp").alias("completion_timestamp"),
    )

    # Opens and completes to test.
    opens = events.filter(
        pl.col("event_type").is_in(["module_open", "module_complete"])
    ).select("learner_id", "module_id", "event_timestamp", "event_type")

    # Join open/completes to dependencies on successor side.
    dep = curriculum_dependencies.filter(
        pl.col("dependency_type") == "prerequisite"
    ).select(
        pl.col("predecessor_module_id"),
        pl.col("successor_module_id"),
        pl.col("dependency_type"),
    )
    joined = opens.join(
        dep, left_on="module_id", right_on="successor_module_id", how="inner"
    )

    # Join in predecessor completion times (or null if unmet).
    joined = joined.join(
        completions,
        left_on=["learner_id", "predecessor_module_id"],
        right_on=["learner_id", "completed_module_id"],
        how="left",
    )

    # Violation: no prior completion OR completion timestamp >= event ts.
    violations = joined.filter(
        pl.col("completion_timestamp").is_null()
        | (pl.col("completion_timestamp") >= pl.col("event_timestamp"))
    ).select(
        "learner_id",
        "module_id",
        "event_timestamp",
        "predecessor_module_id",
        "dependency_type",
    )

    return violations
