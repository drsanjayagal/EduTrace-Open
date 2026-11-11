"""Feedback-event generator.

Feedback is attached to attempts (one feedback row per attempt, by design).
Some attempts receive no feedback (auto-graded quizzes submitted ``missed``
are the clearest case). The ``FEEDBACK_TYPE_WEIGHTS`` distribution determines
which type of feedback is issued; the delay is log-normal per type; view
probability depends on delay and engagement.

The row key is ``(attempt_num, 0, 0, 0)`` — a single draw per attempt — so
chunk boundaries cannot alter values.
"""

from __future__ import annotations

from datetime import timedelta

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import (
    FEEDBACK_DELAY_LOG_NORMAL,
    FEEDBACK_TYPE_WEIGHTS,
)
from edutrace.utils.ids import (
    PREFIX_FEEDBACK,
    format_id,
    parse_id,
    row_key_from_ints,
)
from edutrace.utils.random_state import RandomStateManager


def generate_feedback_for_chunk(
    config: EduTraceConfig,
    rng: RandomStateManager,
    attempts_chunk: pl.DataFrame,
    learners: pl.DataFrame,
    *,
    feedback_id_start: int = 1,
) -> tuple[pl.DataFrame, int]:
    """Generate feedback events for a chunk of attempts.

    Returns ``(feedback_df, next_feedback_id_start)``.
    """
    if attempts_chunk.is_empty():
        return _empty(), feedback_id_start

    engagement_by_learner: dict[int, float] = {}
    for row in learners.iter_rows(named=True):
        engagement_by_learner[parse_id(row["learner_id"])[1]] = float(
            row["initial_engagement_profile"]
        )

    type_labels = tuple(FEEDBACK_TYPE_WEIGHTS.keys())
    type_probs = [FEEDBACK_TYPE_WEIGHTS[k] for k in type_labels]
    total = sum(type_probs)
    type_probs = [p / total for p in type_probs]

    rows: list[dict] = []
    feedback_counter = feedback_id_start

    for att_row in attempts_chunk.iter_rows(named=True):
        attempt_id = att_row["attempt_id"]
        attempt_num = parse_id(attempt_id)[1]
        learner_num = parse_id(att_row["learner_id"])[1]
        engagement = engagement_by_learner.get(learner_num, 0.5)

        if att_row["submission_status"] == "missed":
            continue

        r = rng.row_rng("feedback_event", row_key_from_ints(attempt_num, 0, 0, 0))
        if r.random() >= 0.90:
            continue

        ftype_idx = int(r.choice(len(type_labels), p=type_probs))
        ftype = type_labels[ftype_idx]

        params = FEEDBACK_DELAY_LOG_NORMAL[ftype]
        delay_hours = float(max(0.0, r.lognormal(params["mu"], params["sigma"])))

        viewed_p = (
            0.65 + 0.25 * engagement - 0.15 * min(1.0, delay_hours / (7.0 * 24.0))
        )
        viewed_p = min(0.95, max(0.05, viewed_p))
        viewed = bool(r.random() < viewed_p)

        score_fraction = (
            float(att_row["score"]) / float(att_row["maximum_score"])
            if float(att_row["maximum_score"]) > 0
            else 0.0
        )
        revision_p = 0.35 * (1.0 - score_fraction) * (1.0 if viewed else 0.0)
        revision = bool(r.random() < revision_p)

        feedback_timestamp = att_row["attempt_timestamp"] + timedelta(hours=delay_hours)

        rows.append(
            {
                "feedback_id": format_id(PREFIX_FEEDBACK, feedback_counter),
                "attempt_id": attempt_id,
                "learner_id": att_row["learner_id"],
                "feedback_timestamp": feedback_timestamp,
                "feedback_type": ftype,
                "feedback_delay_hours": round(delay_hours, 3),
                "feedback_viewed": viewed,
                "revision_flag": revision,
            }
        )
        feedback_counter += 1

    if not rows:
        return _empty(), feedback_counter

    df = pl.from_dicts(rows, infer_schema_length=len(rows)).with_columns(
        [
            pl.col("feedback_id").cast(pl.Utf8),
            pl.col("attempt_id").cast(pl.Utf8),
            pl.col("learner_id").cast(pl.Utf8),
            pl.col("feedback_timestamp").cast(pl.Datetime("us")),
            pl.col("feedback_type").cast(pl.Utf8),
            pl.col("feedback_delay_hours").cast(pl.Float64),
            pl.col("feedback_viewed").cast(pl.Boolean),
            pl.col("revision_flag").cast(pl.Boolean),
        ]
    )
    return df, feedback_counter


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "feedback_id": pl.Utf8,
            "attempt_id": pl.Utf8,
            "learner_id": pl.Utf8,
            "feedback_timestamp": pl.Datetime("us"),
            "feedback_type": pl.Utf8,
            "feedback_delay_hours": pl.Float64,
            "feedback_viewed": pl.Boolean,
            "revision_flag": pl.Boolean,
        }
    )
