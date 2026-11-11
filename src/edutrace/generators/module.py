"""Module generator.

Each course is split into ``num_modules_per_course`` modules with
``module_sequence`` in 1..N. Module difficulty is inherited from the parent
course with a small additive perturbation. Learning objectives are
synthetic strings; the model does not claim alignment with any real
curriculum.

Estimated learning hours follow Gamma(k=3.0, theta=4.0) hours per module,
with a mild bump for later sequences within the course.
"""

from __future__ import annotations

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.utils.ids import PREFIX_MODULE, format_ids
from edutrace.utils.random_state import RandomStateManager


def generate_modules(
    config: EduTraceConfig,
    rng: RandomStateManager,
    courses: pl.DataFrame,
) -> pl.DataFrame:
    n_mod = config.generation.num_modules_per_course
    if courses.is_empty() or n_mod <= 0:
        return _empty()

    course_ids = courses["course_id"].to_list()
    course_difficulties = courses["difficulty_level"].to_list()

    rows: list[dict] = []
    counter = 0

    for course_id, course_diff in zip(course_ids, course_difficulties, strict=True):
        for seq in range(1, n_mod + 1):
            counter += 1
            r = rng.row_rng("module", counter)

            perturbation = float(r.normal(0.0, 0.05))
            difficulty = float(min(1.0, max(0.0, course_diff + perturbation)))
            # Longer study hours for later modules in the course.
            base_hours = float(r.gamma(3.0, 4.0))
            hours = float(base_hours + 2.0 * (seq - 1))
            objectives = (
                f"By the end of module {seq} learners should be able to "
                f"apply the core concepts at difficulty ~{difficulty:.2f}."
            )

            rows.append(
                {
                    "module_id": format_ids(PREFIX_MODULE, [counter])[0],
                    "course_id": course_id,
                    "module_name": f"Module {seq} of {course_id}",
                    "module_sequence": seq,
                    "learning_objectives": objectives,
                    "estimated_learning_hours": hours,
                }
            )

    if not rows:
        return _empty()

    return pl.from_dicts(rows).with_columns(
        [
            pl.col("module_id").cast(pl.Utf8),
            pl.col("course_id").cast(pl.Utf8),
            pl.col("module_name").cast(pl.Utf8),
            pl.col("module_sequence").cast(pl.Int64),
            pl.col("learning_objectives").cast(pl.Utf8),
            pl.col("estimated_learning_hours").cast(pl.Float64),
        ]
    )


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "module_id": pl.Utf8,
            "course_id": pl.Utf8,
            "module_name": pl.Utf8,
            "module_sequence": pl.Int64,
            "learning_objectives": pl.Utf8,
            "estimated_learning_hours": pl.Float64,
        }
    )
