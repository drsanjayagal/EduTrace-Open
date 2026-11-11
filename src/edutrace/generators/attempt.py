"""Assessment-attempt generator.

Each (learner, enrolment, assessment_item) triple produces 0..N attempts.
N is 1 for quizzes/formative checks/exams and 1..3 for assignments. The
probability an attempt occurs at all is
``ATTEMPT_PROBABILITY_BY_TYPE[type]``.

Attempt timestamps are placed inside the item's module week (module
``module_sequence`` as week-in-semester) — a modelling assumption, since
modules are the finest grain we currently track.

Deterministic row keys
----------------------
Every attempt's randomness is keyed on
``(learner_num, enrolment_num, item_num, attempt_number)`` via
``row_key_from_ints``. Therefore chunk boundaries cannot change any
attempt's values.

Attempt ID assignment uses a caller-provided ``attempt_id_start`` counter,
exactly like ``learning_event.py``. The orchestrator chains chunks.

Public API
----------
* :func:`build_attempt_indexes` — build the learner / module / item maps
  once per run and pass them via ``indexes=``.
* :func:`generate_attempts_for_chunk` — generate attempts for a chunk of
  enrolments.
"""

from __future__ import annotations

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import (
    ATTEMPT_PROBABILITY_BY_TYPE,
    LATE_SUBMISSION_BASE,
    SUBMISSION_STATUS_WEIGHTS,
)
from edutrace.simulation.assessment_models import (
    sample_attempt_duration,
    score_attempt,
)
from edutrace.simulation.temporal_models import (
    sample_channel,
    sample_timestamp_in_week,
)
from edutrace.utils.dates import AcademicCalendar
from edutrace.utils.ids import (
    PREFIX_ATTEMPT,
    format_id,
    parse_id,
    row_key_from_ints,
)
from edutrace.utils.random_state import RandomStateManager

_LATE_ELIGIBLE_TYPES = frozenset({"assignment", "project"})
_RESUBMITTABLE_TYPES = frozenset({"assignment", "project"})


def build_attempt_indexes(
    learners: pl.DataFrame,
    modules: pl.DataFrame,
    assessment_items: pl.DataFrame,
) -> dict:
    """Build the indexes consumed by :func:`generate_attempts_for_chunk`.

    Build once per pipeline run and pass via ``indexes=`` to avoid
    rebuilding inside each chunk.

    Returns a dict with keys ``traits``, ``modules_by_course``,
    ``items_by_module``.
    """
    traits: dict[int, tuple[float, float]] = {}
    for row in learners.iter_rows(named=True):
        learner_num = parse_id(row["learner_id"])[1]
        traits[learner_num] = (
            float(row["baseline_preparedness"]),
            float(row["initial_engagement_profile"]),
        )

    modules_by_course: dict[str, list[dict]] = {}
    for row in modules.iter_rows(named=True):
        modules_by_course.setdefault(row["course_id"], []).append(row)

    items_by_module: dict[str, list[dict]] = {}
    for row in assessment_items.iter_rows(named=True):
        items_by_module.setdefault(row["module_id"], []).append(row)

    return {
        "traits": traits,
        "modules_by_course": modules_by_course,
        "items_by_module": items_by_module,
    }


def generate_attempts_for_chunk(
    config: EduTraceConfig,
    rng: RandomStateManager,
    enrolments_chunk: pl.DataFrame,
    assessment_items: pl.DataFrame,
    modules: pl.DataFrame,
    learners: pl.DataFrame,
    calendar: AcademicCalendar,
    *,
    attempt_id_start: int = 1,
    indexes: dict | None = None,
) -> tuple[pl.DataFrame, int]:
    """Generate attempts for one chunk of enrolments.

    Returns ``(attempts_df, next_attempt_id_start)``.
    """
    if enrolments_chunk.is_empty() or assessment_items.is_empty():
        return _empty(), attempt_id_start

    idx = indexes or build_attempt_indexes(
        learners, modules, assessment_items
    )
    traits = idx["traits"]
    modules_by_course = idx["modules_by_course"]
    items_by_module = idx["items_by_module"]

    sub_status_labels = tuple(SUBMISSION_STATUS_WEIGHTS.keys())
    sub_status_probs = [
        SUBMISSION_STATUS_WEIGHTS[k] for k in sub_status_labels
    ]
    total = sum(sub_status_probs)
    sub_status_probs = [p / total for p in sub_status_probs]

    rows: list[dict] = []
    attempt_counter = attempt_id_start

    for enr_row in enrolments_chunk.iter_rows(named=True):
        learner_id = enr_row["learner_id"]
        learner_num = parse_id(learner_id)[1]
        enrolment_id = enr_row["enrolment_id"]
        enrolment_num = parse_id(enrolment_id)[1]
        course_id = enr_row["course_id"]

        trait = traits.get(learner_num)
        if trait is None:
            continue
        preparedness, engagement = trait

        course_modules = sorted(
            modules_by_course.get(course_id, []),
            key=lambda m: int(m["module_sequence"]),
        )
        if not course_modules:
            continue

        sem_within_year = int(enr_row["semester"])
        acad_year = int(enr_row["academic_year"])
        start_year = calendar.start.year
        global_sem_idx = (
            (acad_year - start_year) * calendar.semesters_per_year
            + (sem_within_year - 1)
        )
        if global_sem_idx < 0 or global_sem_idx >= calendar.total_semesters:
            continue

        for mod_row in course_modules:
            module_id = mod_row["module_id"]
            module_sequence = int(mod_row["module_sequence"])
            academic_week = min(
                max(module_sequence, 1), calendar.weeks_per_semester
            )
            week_start = calendar.week_start(global_sem_idx, academic_week)

            module_items = items_by_module.get(module_id, [])
            if not module_items:
                continue

            for item in module_items:
                item_id = item["assessment_item_id"]
                item_num = parse_id(item_id)[1]
                atype = item["assessment_type"]
                item_difficulty = float(item["difficulty"])
                max_score = float(item["maximum_score"])

                attempt_prob = ATTEMPT_PROBABILITY_BY_TYPE.get(atype, 1.0)
                max_attempts = 3 if atype in _RESUBMITTABLE_TYPES else 1

                for attempt_number in range(1, max_attempts + 1):
                    key = row_key_from_ints(
                        learner_num, enrolment_num, item_num, attempt_number
                    )
                    r = rng.row_rng("assessment_attempt", key)

                    attempt_p = (
                        attempt_prob
                        if attempt_number == 1
                        else attempt_prob * 0.55
                    )
                    if r.random() >= attempt_p:
                        break

                    channel = sample_channel(r)
                    timestamp = sample_timestamp_in_week(
                        week_start, channel, r
                    )

                    score = score_attempt(
                        preparedness=preparedness,
                        engagement=engagement,
                        item_difficulty=item_difficulty,
                        prior_attempts=attempt_number - 1,
                        maximum_score=max_score,
                        rng=r,
                    )

                    duration = sample_attempt_duration(atype, rng=r)

                    submission_status = str(
                        r.choice(sub_status_labels, p=sub_status_probs)
                    )

                    late = False
                    if atype in _LATE_ELIGIBLE_TYPES:
                        p_late = LATE_SUBMISSION_BASE * (1.0 - preparedness)
                        late = bool(r.random() < p_late)

                    rows.append(
                        {
                            "attempt_id": format_id(
                                PREFIX_ATTEMPT, attempt_counter
                            ),
                            "learner_id": learner_id,
                            "enrolment_id": enrolment_id,
                            "assessment_item_id": item_id,
                            "attempt_number": attempt_number,
                            "attempt_timestamp": timestamp,
                            "score": score,
                            "maximum_score": max_score,
                            "duration_seconds": int(duration),
                            "submission_status": submission_status,
                            "late_submission_flag": late,
                        }
                    )
                    attempt_counter += 1

                    if (
                        atype not in _RESUBMITTABLE_TYPES
                        or score >= 0.7 * max_score
                    ):
                        break

    if not rows:
        return _empty(), attempt_counter

    df = pl.from_dicts(
        rows, infer_schema_length=len(rows)
    ).with_columns(
        [
            pl.col("attempt_id").cast(pl.Utf8),
            pl.col("learner_id").cast(pl.Utf8),
            pl.col("enrolment_id").cast(pl.Utf8),
            pl.col("assessment_item_id").cast(pl.Utf8),
            pl.col("attempt_number").cast(pl.Int64),
            pl.col("attempt_timestamp").cast(pl.Datetime("us")),
            pl.col("score").cast(pl.Float64),
            pl.col("maximum_score").cast(pl.Float64),
            pl.col("duration_seconds").cast(pl.Int64),
            pl.col("submission_status").cast(pl.Utf8),
            pl.col("late_submission_flag").cast(pl.Boolean),
        ]
    )
    return df, attempt_counter


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "attempt_id": pl.Utf8,
            "learner_id": pl.Utf8,
            "enrolment_id": pl.Utf8,
            "assessment_item_id": pl.Utf8,
            "attempt_number": pl.Int64,
            "attempt_timestamp": pl.Datetime("us"),
            "score": pl.Float64,
            "maximum_score": pl.Float64,
            "duration_seconds": pl.Int64,
            "submission_status": pl.Utf8,
            "late_submission_flag": pl.Boolean,
        }
    )
