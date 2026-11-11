"""Timestamped learning-event generator.

This is the heaviest generator in the project. It is written to be
chunk-safe:

* Row keys are derived from ``(learner_num, global_sem_idx, academic_week, seq)``
  via ``row_key_from_ints`` — never from a global running counter.
* Chunk size is an argument to the top-level function and is applied only
  by the caller iterating over chunks of learners.
* Event IDs are assigned from a *global* counter that the caller chains via
  ``event_id_start`` / the returned ``next_event_id_start``.

Public API
----------
* :func:`build_resource_index` — build the ``module_id`` → resources map
  once per run and pass it via ``indexes=``.
* :func:`generate_learning_events_for_chunk` — generate events for a chunk
  of enrolments.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import (
    ALL_EVENT_TYPES as _ALL_EVENTS,
)
from edutrace.constants import (
    EVENT_TYPE_WEIGHTS_BY_PHASE,
    OTHER_DURATION_RANGE,
    QUIZ_DURATION_RANGE,
    READING_DURATION_RANGE,
    VIDEO_DURATION_RANGE,
)
from edutrace.simulation.behavioural_models import (
    LearnerBehaviour,
    next_engagement_state,
    sample_weekly_event_count,
    week_phase,
)
from edutrace.simulation.temporal_models import (
    sample_channel,
    sample_duration_seconds,
    sample_timestamp_in_week,
)
from edutrace.utils.dates import AcademicCalendar
from edutrace.utils.ids import (
    PREFIX_EVENT,
    format_id,
    parse_id,
    row_key_from_ints,
)
from edutrace.utils.random_state import RandomStateManager

_COMPLETION_EVENT_TYPES = frozenset(
    {
        "video_complete",
        "quiz_submit",
        "assignment_submit",
        "module_complete",
        "feedback_view",
    }
)

_INSTANTANEOUS_EVENT_TYPES = frozenset(
    {
        "login",
        "logout",
        "module_open",
        "module_complete",
        "learning_path_access",
    }
)


def build_resource_index(resources: pl.DataFrame) -> dict[str, list[dict]]:
    """Build the ``module_id`` → resource-rows index.

    Callers should build this once per pipeline run and pass it via
    ``indexes={"resources_by_module": ...}`` to avoid rebuilding per chunk.
    """
    out: dict[str, list[dict]] = {}
    for res_row in resources.iter_rows(named=True):
        out.setdefault(res_row["module_id"], []).append(res_row)
    return out


def generate_learning_events_for_chunk(
    config: EduTraceConfig,
    rng: RandomStateManager,
    enrolments_chunk: pl.DataFrame,
    resources: pl.DataFrame,
    behaviours: dict[int, LearnerBehaviour],
    calendar: AcademicCalendar,
    *,
    event_id_start: int = 1,
    indexes: dict | None = None,
) -> tuple[pl.DataFrame, int]:
    """Generate events for one chunk of enrolments.

    Parameters
    ----------
    enrolments_chunk:
        Slice of the enrolment table. Each row contributes events for its
        learner.
    resources:
        Full learning_resource table (needed for FK validity).
    behaviours:
        Mapping ``learner_num → LearnerBehaviour``.
    calendar:
        Academic calendar. ``weeks_per_semester`` is read from it.
    event_id_start:
        First event-id number for this chunk (1-based). The generator
        returns the next unused number so the caller can chain chunks.
    indexes:
        Optional pre-built indexes. Currently supports the key
        ``"resources_by_module"`` whose value comes from
        :func:`build_resource_index`. When omitted, the index is built
        locally (correct but slower).

    Returns
    -------
    (df, next_event_id_start)
    """
    if enrolments_chunk.is_empty():
        return _empty(), event_id_start

    if indexes is not None and "resources_by_module" in indexes:
        resources_by_module = indexes["resources_by_module"]
    else:
        resources_by_module = build_resource_index(resources)

    weeks_per_semester = calendar.weeks_per_semester

    learner_state: dict[int, LearnerBehaviour] = dict(behaviours)

    enr_by_learner: dict[int, list[dict]] = {}
    for row in enrolments_chunk.iter_rows(named=True):
        learner_num = parse_id(row["learner_id"])[1]
        enr_by_learner.setdefault(learner_num, []).append(row)

    event_rows: list[dict] = []
    event_counter = event_id_start

    for learner_num, rows in enr_by_learner.items():
        behaviour = learner_state.get(learner_num)
        if behaviour is None:
            continue

        rows.sort(
            key=lambda r: (
                int(r["academic_year"]),
                int(r["semester"]),
                r["course_id"],
            )
        )

        for enrolment_row in rows:
            enrolment_id = enrolment_row["enrolment_id"]
            course_id = enrolment_row["course_id"]

            sem_within_year = int(enrolment_row["semester"])
            acad_year = int(enrolment_row["academic_year"])

            start_year = calendar.start.year
            global_sem_idx = (
                (acad_year - start_year) * calendar.semesters_per_year
                + (sem_within_year - 1)
            )
            if global_sem_idx < 0 or global_sem_idx >= calendar.total_semesters:
                continue

            course_module_ids = sorted(
                {
                    res["module_id"]
                    for mod_resources in resources_by_module.values()
                    for res in mod_resources
                    if res["course_id"] == course_id
                }
            )
            if not course_module_ids:
                continue

            for academic_week in range(1, weeks_per_semester + 1):
                week_rng = rng.row_rng(
                    "learning_event",
                    row_key_from_ints(
                        learner_num, global_sem_idx, academic_week, 0
                    ),
                )

                count = sample_weekly_event_count(
                    behaviour, academic_week, weeks_per_semester, week_rng
                )
                if count <= 0:
                    new_state = next_engagement_state(
                        behaviour.engagement_state, week_rng
                    )
                    behaviour = LearnerBehaviour(
                        learner_key=behaviour.learner_key,
                        base_event_rate=behaviour.base_event_rate,
                        engagement_state=new_state,
                        preference_bias=behaviour.preference_bias,
                    )
                    learner_state[learner_num] = behaviour
                    continue

                week_start = calendar.week_start(global_sem_idx, academic_week)
                phase = week_phase(academic_week, weeks_per_semester)
                phase_weights = EVENT_TYPE_WEIGHTS_BY_PHASE[phase]
                phase_labels = tuple(_ALL_EVENTS)

                for seq in range(1, count + 1):
                    event_rng = rng.row_rng(
                        "learning_event",
                        row_key_from_ints(
                            learner_num, global_sem_idx, academic_week, seq
                        ),
                    )
                    event_type = str(
                        event_rng.choice(phase_labels, p=phase_weights)
                    )
                    channel = sample_channel(event_rng)
                    timestamp = sample_timestamp_in_week(
                        week_start, channel, event_rng
                    )

                    module_id = str(event_rng.choice(course_module_ids))
                    module_resources = resources_by_module.get(module_id, [])
                    if module_resources:
                        weights = np.array(
                            [
                                behaviour.preference_bias.get(
                                    res["resource_type"], 1.0
                                )
                                for res in module_resources
                            ],
                            dtype=float,
                        )
                        weights = weights / weights.sum()
                        res_idx = int(
                            event_rng.choice(len(module_resources), p=weights)
                        )
                        resource_id: str | None = module_resources[res_idx][
                            "resource_id"
                        ]
                    else:
                        resource_id = None

                    if event_type in _INSTANTANEOUS_EVENT_TYPES:
                        duration_seconds = 0
                    else:
                        duration_seconds = sample_duration_seconds(
                            event_type,
                            event_rng,
                            video_range=VIDEO_DURATION_RANGE,
                            reading_range=READING_DURATION_RANGE,
                            quiz_range=QUIZ_DURATION_RANGE,
                            other_range=OTHER_DURATION_RANGE,
                        )

                    completion = event_type in _COMPLETION_EVENT_TYPES

                    event_rows.append(
                        {
                            "event_id": format_id(PREFIX_EVENT, event_counter),
                            "learner_id": enrolment_row["learner_id"],
                            "enrolment_id": enrolment_id,
                            "course_id": course_id,
                            "module_id": module_id,
                            "resource_id": resource_id,
                            "event_timestamp": timestamp,
                            "event_type": event_type,
                            "event_duration_seconds": int(duration_seconds),
                            "interaction_channel": channel,
                            "completion_flag": completion,
                            "event_sequence": seq,
                        }
                    )
                    event_counter += 1

                new_state = next_engagement_state(
                    behaviour.engagement_state, week_rng
                )
                behaviour = LearnerBehaviour(
                    learner_key=behaviour.learner_key,
                    base_event_rate=behaviour.base_event_rate,
                    engagement_state=new_state,
                    preference_bias=behaviour.preference_bias,
                )
                learner_state[learner_num] = behaviour

    if not event_rows:
        return _empty(), event_counter

    df = pl.from_dicts(
        event_rows, infer_schema_length=len(event_rows)
    ).with_columns(
        [
            pl.col("event_id").cast(pl.Utf8),
            pl.col("learner_id").cast(pl.Utf8),
            pl.col("enrolment_id").cast(pl.Utf8),
            pl.col("course_id").cast(pl.Utf8),
            pl.col("module_id").cast(pl.Utf8),
            pl.col("resource_id").cast(pl.Utf8),
            pl.col("event_timestamp").cast(pl.Datetime("us")),
            pl.col("event_type").cast(pl.Utf8),
            pl.col("event_duration_seconds").cast(pl.Int64),
            pl.col("interaction_channel").cast(pl.Utf8),
            pl.col("completion_flag").cast(pl.Boolean),
            pl.col("event_sequence").cast(pl.Int64),
        ]
    )

    return df, event_counter


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "event_id": pl.Utf8,
            "learner_id": pl.Utf8,
            "enrolment_id": pl.Utf8,
            "course_id": pl.Utf8,
            "module_id": pl.Utf8,
            "resource_id": pl.Utf8,
            "event_timestamp": pl.Datetime("us"),
            "event_type": pl.Utf8,
            "event_duration_seconds": pl.Int64,
            "interaction_channel": pl.Utf8,
            "completion_flag": pl.Boolean,
            "event_sequence": pl.Int64,
        }
    )
