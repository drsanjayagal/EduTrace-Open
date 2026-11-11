"""Progression-event generator.

For each learner, for each semester from their admission until the
programme's final semester, emit one progression_event at the semester's
end.

**Cumulative semantics.** ``credits_attempted`` and ``credits_earned``
are cumulative up to and including that semester.

**Timestamp derivation.** The semester end date is the calendar's
``semester_end`` for the *calendar-global* semester index of that
(academic_year, semester) pair, i.e.::

    global_calendar_idx =
        (academic_year - calendar.start.year) * semesters_per_year
        + (semester_within_year - 1)

This is the same index enrolment and attempt generation use. When that
index exceeds the calendar's modelled range (a learner admitted near the
end of the calendar who progresses beyond it), the semester end is
extrapolated forward by a fixed semester length. This prevents two bugs:

* progression events for late-admitted learners firing in the calendar's
  early years, which would produce false leakage failures;
* ``calendar.semester_end`` raising ``ValueError`` for out-of-range indices.

**Event timestamp** is ``semester_end + 1 day at 06:00`` so that any
attempt or feedback on the semester's last day is strictly before the
progression event.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import CompletionStatus, ProgressionType
from edutrace.simulation.academic_models import (
    classify_progression_outcome,
    classify_standing,
    compute_semester_gpa,
)
from edutrace.utils.dates import INTERSEMESTER_GAP_WEEKS, AcademicCalendar
from edutrace.utils.ids import PREFIX_PROGRESSION, format_id
from edutrace.utils.random_state import RandomStateManager


def _extended_semester_end(
    calendar: AcademicCalendar, global_calendar_idx: int
) -> date:
    """Return the end date of the given calendar-global semester index.

    If ``global_calendar_idx`` is within the calendar's range, use
    ``calendar.semester_end``. Otherwise, extrapolate forward from the last
    valid semester using the standard semester length.
    """
    if 0 <= global_calendar_idx < calendar.total_semesters:
        return calendar.semester_end(global_calendar_idx)

    if global_calendar_idx < 0:
        # Extrapolate backwards. Not expected in practice but consistent.
        last = calendar.semester_end(0)
        semester_days = (
            calendar.weeks_per_semester + INTERSEMESTER_GAP_WEEKS
        ) * 7
        return last + timedelta(days=global_calendar_idx * semester_days)

    last = calendar.semester_end(calendar.total_semesters - 1)
    semester_days = (
        calendar.weeks_per_semester + INTERSEMESTER_GAP_WEEKS
    ) * 7
    offset = global_calendar_idx - (calendar.total_semesters - 1)
    return last + timedelta(days=offset * semester_days)


def generate_progression_events(
    config: EduTraceConfig,
    rng: RandomStateManager,
    learners: pl.DataFrame,
    enrolments: pl.DataFrame,
    courses: pl.DataFrame,
    programmes: pl.DataFrame,
    *,
    progression_id_start: int = 1,
) -> tuple[pl.DataFrame, int]:
    """Return ``(progression_df, next_progression_id_start)``."""
    _ = rng  # no stochastic draws

    if learners.is_empty() or enrolments.is_empty():
        return _empty(), progression_id_start

    calendar = AcademicCalendar(
        start=date.fromisoformat(config.generation.academic_calendar_start),
        semesters_per_year=config.generation.semesters_per_year,
        weeks_per_semester=config.generation.weeks_per_semester,
        num_academic_years=config.generation.num_academic_years,
    )

    course_credits: dict[str, int] = {
        row["course_id"]: int(row["credit_value"])
        for row in courses.iter_rows(named=True)
    }

    prog_duration = {
        row["programme_id"]: int(row["duration_semesters"])
        for row in programmes.iter_rows(named=True)
    }

    enrolments_by_learner_sem: dict[
        tuple[str, int, int], list[dict]
    ] = {}
    for row in enrolments.iter_rows(named=True):
        key = (
            row["learner_id"],
            int(row["academic_year"]),
            int(row["semester"]),
        )
        enrolments_by_learner_sem.setdefault(key, []).append(row)

    rows: list[dict] = []
    counter = progression_id_start

    for learner_row in learners.iter_rows(named=True):
        learner_id = learner_row["learner_id"]
        programme_id = learner_row["programme_id"]
        admission_year = int(learner_row["admission_year"])
        max_sem = min(
            prog_duration.get(programme_id, 0),
            config.generation.num_academic_years
            * config.generation.semesters_per_year,
        )
        if max_sem <= 0:
            continue

        cumulative_attempted = 0
        cumulative_earned = 0

        for within_prog_sem in range(1, max_sem + 1):
            global_sem_idx = within_prog_sem - 1
            academic_year = admission_year + (
                global_sem_idx // config.generation.semesters_per_year
            )
            semester_within_year = (
                global_sem_idx % config.generation.semesters_per_year
            ) + 1

            sem_enrs = enrolments_by_learner_sem.get(
                (learner_id, academic_year, semester_within_year), []
            )

            sem_attempted = sum(
                course_credits.get(e["course_id"], 0)
                for e in sem_enrs
                if e["enrolment_status"] != "withdrawn"
            )
            sem_earned = sum(
                course_credits.get(e["course_id"], 0)
                for e in sem_enrs
                if e["completion_status"] == CompletionStatus.COMPLETED.value
                and e["enrolment_status"] != "withdrawn"
            )

            grades = [e.get("final_grade") for e in sem_enrs]
            credits_list = [
                course_credits.get(e["course_id"], 0) for e in sem_enrs
            ]
            gpa = compute_semester_gpa(credits_list, grades)

            cumulative_attempted += sem_attempted
            cumulative_earned += sem_earned

            outcome = classify_progression_outcome(
                cumulative_attempted, cumulative_earned, gpa
            )
            standing = classify_standing(gpa)

            # Calendar-global semester index (matches enrolment and attempt
            # generation for this learner's semester).
            global_calendar_idx = (
                (academic_year - calendar.start.year)
                * calendar.semesters_per_year
                + (semester_within_year - 1)
            )

            sem_end = _extended_semester_end(calendar, global_calendar_idx)
            ts = datetime.combine(
                sem_end + timedelta(days=1), time(hour=6, minute=0, second=0)
            )

            rows.append(
                {
                    "progression_event_id": format_id(
                        PREFIX_PROGRESSION, counter
                    ),
                    "learner_id": learner_id,
                    "programme_id": programme_id,
                    "event_timestamp": ts,
                    "progression_type": ProgressionType.SEMESTER_END.value,
                    "semester_number": within_prog_sem,
                    "academic_standing": standing,
                    "credits_attempted": cumulative_attempted,
                    "credits_earned": cumulative_earned,
                    "progression_outcome": outcome,
                }
            )
            counter += 1

    if not rows:
        return _empty(), counter

    df = pl.from_dicts(rows, infer_schema_length=len(rows)).with_columns(
        [
            pl.col("progression_event_id").cast(pl.Utf8),
            pl.col("learner_id").cast(pl.Utf8),
            pl.col("programme_id").cast(pl.Utf8),
            pl.col("event_timestamp").cast(pl.Datetime("us")),
            pl.col("progression_type").cast(pl.Utf8),
            pl.col("semester_number").cast(pl.Int64),
            pl.col("academic_standing").cast(pl.Utf8),
            pl.col("credits_attempted").cast(pl.Int64),
            pl.col("credits_earned").cast(pl.Int64),
            pl.col("progression_outcome").cast(pl.Utf8),
        ]
    )
    return df, counter


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "progression_event_id": pl.Utf8,
            "learner_id": pl.Utf8,
            "programme_id": pl.Utf8,
            "event_timestamp": pl.Datetime("us"),
            "progression_type": pl.Utf8,
            "semester_number": pl.Int64,
            "academic_standing": pl.Utf8,
            "credits_attempted": pl.Int64,
            "credits_earned": pl.Int64,
            "progression_outcome": pl.Utf8,
        }
    )
