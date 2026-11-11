"""Support-intervention event generator.

For each (learner, semester) pair, compute semester-level risk indicators
from the weekly-engagement and attempts tables, then generate zero or more
interventions for at-risk learners.

The generator operates on already-generated weekly_engagement and attempts
tables. It is called by the orchestrator (Phase 6) after those tables are
complete.

Deterministic row key: ``(learner_num, semester_index, intervention_seq)``.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import (
    MISSED_ITEM_FRACTION_THRESHOLD,
    RISK_ENGAGEMENT_THRESHOLD,
    RISK_GRADE_THRESHOLD,
)
from edutrace.simulation.intervention_models import (
    classify_risk,
    sample_channel,
    sample_intervention_count,
    sample_intervention_type,
    sample_outcome,
    sample_response,
)
from edutrace.utils.ids import (
    PREFIX_SUPPORT,
    format_id,
    parse_id,
    row_key_from_ints,
)
from edutrace.utils.random_state import RandomStateManager


def _build_semester_aggregates(
    weekly_engagement: pl.DataFrame,
    attempts: pl.DataFrame,
    enrolments: pl.DataFrame,
    assessment_items: pl.DataFrame,
) -> dict:
    """Return pre-computed per-(learner, academic_year, semester) aggregates.

    Returns a dict with keys:
      - ``eng_mean``: dict[(learner_id, ay, sem)] → mean engagement_score
      - ``score_mean``: dict[(learner_id, ay, sem)] → mean score fraction * 100
      - ``missed_frac``: dict[(learner_id, ay, sem)] → 1 - attempted/expected
      - ``course_ids_by_sem``: dict[(learner_id, ay, sem)] → [course_id, ...]
    """
    enr_sem = enrolments.select(
        "learner_id", "course_id", "academic_year", "semester"
    )

    # Engagement mean per (learner, ay, sem).
    weekly_with_sem = weekly_engagement.join(
        enr_sem.unique(subset=["learner_id", "course_id"]),
        on=["learner_id", "course_id"],
        how="inner",
    )
    eng_mean = {
        (row["learner_id"], row["academic_year"], row["semester"]): float(
            row["mean_eng"]
        )
        for row in (
            weekly_with_sem.group_by(["learner_id", "academic_year", "semester"])
            .agg(pl.col("engagement_score").mean().alias("mean_eng"))
            .iter_rows(named=True)
        )
    }

    # Attempts by (learner, semester).
    attempt_sem = attempts.join(
        enrolments.select("enrolment_id", "academic_year", "semester"),
        on="enrolment_id",
        how="inner",
    )
    score_mean = {
        (row["learner_id"], row["academic_year"], row["semester"]): float(
            row["mean_frac"]
        )
        * 100.0
        for row in (
            attempt_sem.group_by(["learner_id", "academic_year", "semester"])
            .agg(
                (pl.col("score") / pl.col("maximum_score")).mean().alias("mean_frac")
            )
            .iter_rows(named=True)
        )
    }

    # Attempted items per (learner, semester).
    attempted_counts = {
        (row["learner_id"], row["academic_year"], row["semester"]): int(row["n"])
        for row in (
            attempt_sem.group_by(["learner_id", "academic_year", "semester"])
            .agg(pl.col("assessment_item_id").n_unique().alias("n"))
            .iter_rows(named=True)
        )
    }

    # Expected items: sum of item_count for each course the learner is
    # enrolled in that semester.
    items_per_course = (
        assessment_items.group_by("course_id").agg(
            pl.col("assessment_item_id").n_unique().alias("item_count")
        )
    )
    enrol_course_counts = enr_sem.join(
        items_per_course, on="course_id", how="left"
    )
    expected_items = {
        (row["learner_id"], row["academic_year"], row["semester"]): int(row["n_items"])
        for row in (
            enrol_course_counts.group_by(["learner_id", "academic_year", "semester"])
            .agg(pl.col("item_count").fill_null(0).sum().alias("n_items"))
            .iter_rows(named=True)
        )
    }

    # Course ids per semester via a vectorised group-by-list.
    course_ids_by_sem: dict[tuple[str, int, int], list[str]] = {
        (row["learner_id"], row["academic_year"], row["semester"]): row["course_ids"]
        for row in (
            enr_sem.group_by(["learner_id", "academic_year", "semester"])
            .agg(pl.col("course_id").alias("course_ids"))
            .iter_rows(named=True)
        )
    }

    missed_frac: dict[tuple[str, int, int], float] = {}
    for key, expected in expected_items.items():
        if expected <= 0:
            missed_frac[key] = 0.0
        else:
            attempted = attempted_counts.get(key, 0)
            missed_frac[key] = max(0.0, 1.0 - min(1.0, attempted / expected))

    return {
        "eng_mean": eng_mean,
        "score_mean": score_mean,
        "missed_frac": missed_frac,
        "course_ids_by_sem": course_ids_by_sem,
    }


def generate_support_events(
    config: EduTraceConfig,
    rng: RandomStateManager,
    learners: pl.DataFrame,
    weekly_engagement: pl.DataFrame,
    attempts: pl.DataFrame,
    enrolments: pl.DataFrame,
    assessment_items: pl.DataFrame,
    *,
    support_id_start: int = 1,
    indexes: dict | None = None,
) -> tuple[pl.DataFrame, int]:
    """Return ``(support_df, next_support_id_start)``."""
    if learners.is_empty() or enrolments.is_empty():
        return _empty(), support_id_start

    idx = (
        indexes
        if indexes is not None
        else _build_semester_aggregates(
            weekly_engagement, attempts, enrolments, assessment_items
        )
    )
    eng_mean = idx["eng_mean"]
    score_mean = idx["score_mean"]
    missed_frac = idx["missed_frac"]
    course_ids_by_sem = idx["course_ids_by_sem"]

    rows: list[dict] = []
    counter = support_id_start

    for learner_row in learners.iter_rows(named=True):
        learner_id = learner_row["learner_id"]
        learner_num = parse_id(learner_id)[1]

        learner_enrs = enrolments.filter(pl.col("learner_id") == learner_id)
        if learner_enrs.is_empty():
            continue

        semesters = (
            learner_enrs.select("academic_year", "semester")
            .unique()
            .sort(["academic_year", "semester"])
            .iter_rows(named=True)
        )

        for sem_idx, sem_row in enumerate(semesters):
            ay = int(sem_row["academic_year"])
            sem = int(sem_row["semester"])
            key = (learner_id, ay, sem)

            trigger = classify_risk(
                eng_mean.get(key, 0.5),
                score_mean.get(key, 60.0),
                missed_frac.get(key, 0.0),
                engagement_threshold=RISK_ENGAGEMENT_THRESHOLD,
                grade_threshold=RISK_GRADE_THRESHOLD,
                missed_fraction_threshold=MISSED_ITEM_FRACTION_THRESHOLD,
            )
            if trigger is None:
                continue

            count_key = row_key_from_ints(learner_num, sem_idx, 0, 0)
            r_count = rng.row_rng("support_event", count_key)
            n_interventions = sample_intervention_count(r_count)
            if n_interventions == 0:
                continue

            course_candidates = course_ids_by_sem.get(key, [])
            if not course_candidates:
                continue

            # Intervention base timestamp: ~week 10 of the semester, computed
            # as a fixed 70-day offset from the first enrolment that semester.
            # Modelling assumption (documented).
            first_enr = learner_enrs.filter(
                (pl.col("academic_year") == ay) & (pl.col("semester") == sem)
            )["enrolment_date"].min()
            base_ts = (
                first_enr + timedelta(days=70, hours=10)
                if first_enr is not None
                else datetime(2023, 1, 1, 10, 0, 0)
            )

            for seq in range(1, n_interventions + 1):
                key_seq = row_key_from_ints(learner_num, sem_idx, seq, 0)
                r = rng.row_rng("support_event", key_seq)
                itype = sample_intervention_type(trigger, r)
                channel = sample_channel(r)
                response = sample_response(r)
                outcome = sample_outcome(r)
                followup = bool(
                    r.random() < 0.35 if outcome != "improved" else r.random() < 0.10
                )
                jitter_days = int(r.integers(0, 14))
                ts = base_ts + timedelta(days=jitter_days)
                course_id = str(r.choice(course_candidates))

                rows.append(
                    {
                        "support_event_id": format_id(PREFIX_SUPPORT, counter),
                        "learner_id": learner_id,
                        "course_id": course_id,
                        "intervention_timestamp": ts,
                        "intervention_type": itype,
                        "intervention_trigger": trigger,
                        "support_channel": channel,
                        "response_status": response,
                        "followup_required": followup,
                        "intervention_outcome": outcome,
                    }
                )
                counter += 1

    if not rows:
        return _empty(), counter

    df = pl.from_dicts(rows, infer_schema_length=len(rows)).with_columns(
        [
            pl.col("support_event_id").cast(pl.Utf8),
            pl.col("learner_id").cast(pl.Utf8),
            pl.col("course_id").cast(pl.Utf8),
            pl.col("intervention_timestamp").cast(pl.Datetime("us")),
            pl.col("intervention_type").cast(pl.Utf8),
            pl.col("intervention_trigger").cast(pl.Utf8),
            pl.col("support_channel").cast(pl.Utf8),
            pl.col("response_status").cast(pl.Utf8),
            pl.col("followup_required").cast(pl.Boolean),
            pl.col("intervention_outcome").cast(pl.Utf8),
        ]
    )
    return df, counter


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "support_event_id": pl.Utf8,
            "learner_id": pl.Utf8,
            "course_id": pl.Utf8,
            "intervention_timestamp": pl.Datetime("us"),
            "intervention_type": pl.Utf8,
            "intervention_trigger": pl.Utf8,
            "support_channel": pl.Utf8,
            "response_status": pl.Utf8,
            "followup_required": pl.Boolean,
            "intervention_outcome": pl.Utf8,
        }
    )
