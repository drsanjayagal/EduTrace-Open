"""Course generator.

Each programme has ``num_courses_per_programme`` courses. Courses are
distributed across semesters within the programme duration; each semester
hosts a similar number of courses.

Difficulty is drawn per course from Beta(2.5, 2.0), scaled to [0, 1] and
biased slightly upward for later semesters (harder content). Course type is
categorical: core 55%, elective 25%, lab 15%, seminar 5%. These are
modelling assumptions.

Credit values are 3 or 4 (equal weighting).
"""

from __future__ import annotations

import math

import numpy as np
import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import CourseType
from edutrace.utils.ids import PREFIX_COURSE, format_ids
from edutrace.utils.random_state import RandomStateManager

_COURSE_TYPES = tuple(c.value for c in CourseType)
_COURSE_TYPE_WEIGHTS = (0.55, 0.25, 0.15, 0.05)


def generate_courses(
    config: EduTraceConfig,
    rng: RandomStateManager,
    programmes: pl.DataFrame,
) -> pl.DataFrame:
    n_per = config.generation.num_courses_per_programme
    if programmes.is_empty() or n_per <= 0:
        return _empty()

    prog_ids = programmes["programme_id"].to_list()
    prog_durations = programmes["duration_semesters"].to_list()

    course_rows: list[dict] = []
    course_counter = 0

    for prog_id, duration in zip(prog_ids, prog_durations, strict=True):
        # Distribute courses evenly over semesters; leftover goes to earlier
        # semesters. ``ceil`` guarantees every semester has >= 1 course when
        # num_courses_per_programme >= duration.
        base = n_per // duration
        remainder = n_per % duration
        per_sem = [
            base + (1 if s < remainder else 0) for s in range(duration)
        ]

        for sem_idx, count in enumerate(per_sem, start=1):
            for _ in range(count):
                course_counter += 1
                r = rng.row_rng("course", course_counter)

                # Difficulty rises with semester.
                beta_sample = float(r.beta(2.5, 2.0))
                semester_bias = 0.05 * (sem_idx - 1) / max(duration - 1, 1)
                difficulty = float(min(1.0, max(0.0, 0.5 * beta_sample + 0.25 + semester_bias)))

                ctype = str(r.choice(_COURSE_TYPES, p=_COURSE_TYPE_WEIGHTS))
                # Labs and seminars carry 3 credits; core/elective 4.
                credits = 3 if ctype in (CourseType.LAB.value, CourseType.SEMINAR.value) else 4
                code_suffix = 100 * sem_idx + course_counter % 100
                course_code = f"{prog_id.replace('prog_', 'C')}-{code_suffix:04d}"
                name = f"{ctype.title()} {sem_idx}.{count} ({prog_id})"

                course_rows.append(
                    {
                        "course_id": format_ids(PREFIX_COURSE, [course_counter])[0],
                        "programme_id": prog_id,
                        "course_code": course_code,
                        "course_name": name,
                        "credit_value": credits,
                        "semester": sem_idx,
                        "difficulty_level": difficulty,
                        "course_type": ctype,
                    }
                )

    if not course_rows:
        return _empty()

    return pl.from_dicts(course_rows).with_columns(
        [
            pl.col("course_id").cast(pl.Utf8),
            pl.col("programme_id").cast(pl.Utf8),
            pl.col("course_code").cast(pl.Utf8),
            pl.col("course_name").cast(pl.Utf8),
            pl.col("credit_value").cast(pl.Int64),
            pl.col("semester").cast(pl.Int64),
            pl.col("difficulty_level").cast(pl.Float64),
            pl.col("course_type").cast(pl.Utf8),
        ]
    )


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "course_id": pl.Utf8,
            "programme_id": pl.Utf8,
            "course_code": pl.Utf8,
            "course_name": pl.Utf8,
            "credit_value": pl.Int64,
            "semester": pl.Int64,
            "difficulty_level": pl.Float64,
            "course_type": pl.Utf8,
        }
    )


# Silence unused import warnings in this module while keeping ``math``/``np``
# available for future expansion in Phase 3.
_ = (math, np)
