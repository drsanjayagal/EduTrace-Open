"""Enrolment generator (skeleton + outcome population).

The Phase-2 generator produces a *skeleton* enrolment table where grades
and completion dates are null. The new
:func:`populate_enrolment_outcomes` fills those fields once attempts exist.

Two functions, one source of truth:

* :func:`generate_enrolments` — Phase-2 API, unchanged behaviour.
* :func:`populate_enrolment_outcomes` — Phase-4 API, extended in the
  correction pass to guarantee that ``enrolment_status`` and
  ``completion_status`` are never null (they are declared non-nullable in
  the schema).
"""

from __future__ import annotations

from datetime import date, datetime

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import (
    ENROLMENT_COMPLETION_ATTEMPT_FRACTION,
    PASS_GRADE,
    CompletionStatus,
    CourseType,
    EnrolmentStatus,
)
from edutrace.utils.dates import AcademicCalendar
from edutrace.utils.ids import PREFIX_ENROLMENT, format_ids, row_key_from_ints
from edutrace.utils.random_state import RandomStateManager

ELECTIVE_TAKE_PROB = 0.75
WITHDRAWAL_BASE = 0.15


def generate_enrolments(
    config: EduTraceConfig,
    rng: RandomStateManager,
    learners: pl.DataFrame,
    courses: pl.DataFrame,
) -> pl.DataFrame:
    """Produce the enrolment *skeleton* (no grades, no completion dates)."""
    if learners.is_empty() or courses.is_empty():
        return _empty()

    calendar = AcademicCalendar(
        start=date.fromisoformat(config.generation.academic_calendar_start),
        semesters_per_year=config.generation.semesters_per_year,
        weeks_per_semester=config.generation.weeks_per_semester,
        num_academic_years=config.generation.num_academic_years,
    )

    courses_by_prog_sem: dict[tuple[str, int], list[dict]] = {}
    for row in courses.iter_rows(named=True):
        key = (row["programme_id"], int(row["semester"]))
        courses_by_prog_sem.setdefault(key, []).append(row)

    prog_duration: dict[str, int] = {}
    for row in (
        courses.group_by("programme_id")
        .agg(pl.col("semester").max().alias("max_sem"))
        .iter_rows(named=True)
    ):
        prog_duration[row["programme_id"]] = int(row["max_sem"])

    rows: list[dict] = []
    counter = 0
    max_semester_cap = (
        config.generation.num_academic_years
        * config.generation.semesters_per_year
    )

    for learner_num, learner_row in enumerate(
        learners.iter_rows(named=True), start=1
    ):
        learner_id = learner_row["learner_id"]
        prog = learner_row["programme_id"]
        adm_year = int(learner_row["admission_year"])
        prep = float(learner_row["baseline_preparedness"])

        max_sem = min(prog_duration.get(prog, 0), max_semester_cap)
        if max_sem <= 0:
            continue

        for within_sem in range(1, max_sem + 1):
            available = courses_by_prog_sem.get((prog, within_sem), [])
            if not available:
                continue

            global_sem_idx = within_sem - 1
            enrol_date = calendar.semester_start(global_sem_idx)

            for course in available:
                course_num = int(course["course_id"].split("_")[1])
                row_key = row_key_from_ints(
                    learner_num, global_sem_idx, course_num, 0
                )
                r = rng.row_rng("enrolment", row_key)

                ctype = course["course_type"]
                # Combine the elective/seminar membership test with the
                # take-probability draw into a single condition. Semantically
                # identical to the previous nested form: the draw is only
                # evaluated when the type matches, thanks to short-circuit.
                if (
                    ctype
                    in (CourseType.ELECTIVE.value, CourseType.SEMINAR.value)
                    and r.random() > ELECTIVE_TAKE_PROB
                ):
                    continue

                counter += 1
                withdraw_p = WITHDRAWAL_BASE * (1.0 - prep)
                withdrawn = bool(r.random() < withdraw_p)

                rows.append(
                    {
                        "enrolment_id": format_ids(
                            PREFIX_ENROLMENT, [counter]
                        )[0],
                        "learner_id": learner_id,
                        "course_id": course["course_id"],
                        "academic_year": (
                            adm_year
                            + (
                                global_sem_idx
                                // config.generation.semesters_per_year
                            )
                        ),
                        "semester": (
                            global_sem_idx
                            % config.generation.semesters_per_year
                        )
                        + 1,
                        "enrolment_date": _to_datetime(enrol_date),
                        "completion_date": None,
                        "enrolment_status": (
                            EnrolmentStatus.WITHDRAWN.value
                            if withdrawn
                            else EnrolmentStatus.ACTIVE.value
                        ),
                        "final_grade": None,
                        "completion_status": (
                            CompletionStatus.NOT_COMPLETED.value
                            if withdrawn
                            else CompletionStatus.IN_PROGRESS.value
                        ),
                    }
                )

    if not rows:
        return _empty()

    return pl.from_dicts(rows, infer_schema_length=len(rows)).with_columns(
        [
            pl.col("enrolment_id").cast(pl.Utf8),
            pl.col("learner_id").cast(pl.Utf8),
            pl.col("course_id").cast(pl.Utf8),
            pl.col("academic_year").cast(pl.Int64),
            pl.col("semester").cast(pl.Int64),
            pl.col("enrolment_date").cast(pl.Datetime("us")),
            pl.col("completion_date").cast(pl.Datetime("us")),
            pl.col("enrolment_status").cast(pl.Utf8),
            pl.col("final_grade").cast(pl.Float64),
            pl.col("completion_status").cast(pl.Utf8),
        ]
    )


def populate_enrolment_outcomes(
    config: EduTraceConfig,
    enrolments: pl.DataFrame,
    attempts: pl.DataFrame,
    assessment_items: pl.DataFrame,
) -> pl.DataFrame:
    """Fill final_grade, completion_date, status fields.

    Rules (modelling assumptions):

    * Withdrawn enrolments are untouched (grades stay null).
    * For active enrolments:
        - count distinct items with any attempt
        - if attempts < ``ENROLMENT_COMPLETION_ATTEMPT_FRACTION`` of the
          course's item count → ``not_completed``, grade null, status failed.
        - else → ``completed`` and:
            - ``final_grade`` = weighted mean of best score per item.
            - ``completion_date`` = max attempt timestamp.

    **Never leaves ``enrolment_status`` or ``completion_status`` null.**
    """
    if enrolments.is_empty() or attempts.is_empty() or assessment_items.is_empty():
        return _ensure_status_columns_populated(enrolments)

    items_per_course = (
        assessment_items.group_by("course_id").agg(
            pl.col("assessment_item_id").n_unique().alias("item_count")
        )
    )

    item_lookup = assessment_items.select(
        "assessment_item_id", "course_id", "weight"
    ).rename({"course_id": "item_course_id"})

    attempts_with_course = attempts.join(
        item_lookup, on="assessment_item_id", how="inner"
    )

    best_per_item = (
        attempts_with_course.sort("score", descending=True)
        .group_by(["enrolment_id", "assessment_item_id"])
        .agg(
            pl.col("score").first().alias("best_score"),
            pl.col("attempt_timestamp").first().alias("best_ts"),
            pl.col("weight").first().alias("weight"),
            pl.col("item_course_id").first().alias("course_id"),
        )
    )

    per_enrolment = (
        best_per_item.group_by("enrolment_id")
        .agg(
            pl.col("assessment_item_id").n_unique().alias("n_attempted"),
            (pl.col("best_score") * pl.col("weight"))
            .sum()
            .alias("weighted_sum"),
            pl.col("weight").sum().alias("weight_sum"),
            pl.col("best_ts").max().alias("last_ts"),
        )
    )

    per_enrolment = per_enrolment.join(
        enrolments.select("enrolment_id", "course_id"),
        on="enrolment_id",
        how="left",
    ).join(items_per_course, on="course_id", how="left")

    per_enrolment = per_enrolment.with_columns(
        pl.when(pl.col("item_count").is_null() | (pl.col("item_count") == 0))
        .then(pl.lit(0.0))
        .otherwise(
            pl.col("n_attempted").cast(pl.Float64)
            / pl.col("item_count").cast(pl.Float64)
        )
        .alias("attempted_fraction"),
        pl.when(
            pl.col("weight_sum").is_not_null() & (pl.col("weight_sum") > 0)
        )
        .then((pl.col("weighted_sum") / pl.col("weight_sum")).round(2))
        .otherwise(None)
        .alias("final_grade"),
    )

    insufficient = (
        pl.col("attempted_fraction") < ENROLMENT_COMPLETION_ATTEMPT_FRACTION
    )

    per_enrolment = per_enrolment.with_columns(
        pl.when(insufficient)
        .then(pl.lit(CompletionStatus.NOT_COMPLETED.value))
        .otherwise(pl.lit(CompletionStatus.COMPLETED.value))
        .alias("_new_completion_status"),
        pl.when(insufficient)
        .then(pl.lit(EnrolmentStatus.FAILED.value))
        .when(pl.col("final_grade").is_null())
        .then(pl.lit(EnrolmentStatus.FAILED.value))
        .when(pl.col("final_grade") >= PASS_GRADE)
        .then(pl.lit(EnrolmentStatus.COMPLETED.value))
        .otherwise(pl.lit(EnrolmentStatus.FAILED.value))
        .alias("_new_enrolment_status"),
        pl.when(insufficient)
        .then(pl.lit(None, dtype=pl.Float64))
        .otherwise(pl.col("final_grade"))
        .alias("_new_final_grade"),
        pl.when(insufficient)
        .then(pl.lit(None, dtype=pl.Datetime("us")))
        .otherwise(pl.col("last_ts"))
        .alias("_new_completion_date"),
    )

    enriched = enrolments.join(
        per_enrolment.select(
            "enrolment_id",
            "_new_final_grade",
            "_new_completion_date",
            "_new_enrolment_status",
            "_new_completion_status",
        ),
        on="enrolment_id",
        how="left",
    ).with_columns(
        pl.when(pl.col("enrolment_status") == EnrolmentStatus.WITHDRAWN.value)
        .then(pl.col("final_grade"))
        .otherwise(pl.col("_new_final_grade"))
        .alias("final_grade"),
        pl.when(pl.col("enrolment_status") == EnrolmentStatus.WITHDRAWN.value)
        .then(pl.col("completion_date"))
        .otherwise(pl.col("_new_completion_date"))
        .alias("completion_date"),
        pl.when(pl.col("enrolment_status") == EnrolmentStatus.WITHDRAWN.value)
        .then(pl.col("enrolment_status"))
        .otherwise(pl.col("_new_enrolment_status"))
        .alias("enrolment_status"),
        pl.when(pl.col("enrolment_status") == EnrolmentStatus.WITHDRAWN.value)
        .then(pl.col("completion_status"))
        .otherwise(pl.col("_new_completion_status"))
        .alias("completion_status"),
    ).select(enrolments.columns)

    enriched = _ensure_status_columns_populated(enriched)

    return enriched.with_columns(
        [
            pl.col("final_grade").cast(pl.Float64),
            pl.col("completion_date").cast(pl.Datetime("us")),
            pl.col("enrolment_status").cast(pl.Utf8),
            pl.col("completion_status").cast(pl.Utf8),
        ]
    )


def _ensure_status_columns_populated(df: pl.DataFrame) -> pl.DataFrame:
    """Guarantee ``enrolment_status`` and ``completion_status`` are non-null."""
    if "enrolment_status" not in df.columns or "completion_status" not in df.columns:
        return df
    return df.with_columns(
        pl.when(pl.col("enrolment_status").is_null())
        .then(pl.lit(EnrolmentStatus.FAILED.value))
        .otherwise(pl.col("enrolment_status"))
        .alias("enrolment_status"),
        pl.when(pl.col("completion_status").is_null())
        .then(pl.lit(CompletionStatus.NOT_COMPLETED.value))
        .otherwise(pl.col("completion_status"))
        .alias("completion_status"),
    )


def _to_datetime(d: date | None) -> datetime | None:
    if d is None:
        return None
    return datetime.combine(d, datetime.min.time())


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "enrolment_id": pl.Utf8,
            "learner_id": pl.Utf8,
            "course_id": pl.Utf8,
            "academic_year": pl.Int64,
            "semester": pl.Int64,
            "enrolment_date": pl.Datetime("us"),
            "completion_date": pl.Datetime("us"),
            "enrolment_status": pl.Utf8,
            "final_grade": pl.Float64,
            "completion_status": pl.Utf8,
        }
    )
