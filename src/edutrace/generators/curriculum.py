"""Curriculum dependency generator.

Dependencies are directed edges between modules. Two types are produced
deterministically:

1. **In-course sequence edges.** Module ``k`` depends on module ``k-1``
   within the same course, for k >= 2. This is always emitted.
2. **Cross-course prerequisite edges.** For each course, with probability
   ``CROSS_COURSE_PREREQ_RATE`` (module constant, currently 0.0 → disabled
   by default), the first module of that course depends on the last module
   of some earlier-semester course in the same programme.

The rate is fixed at 0.0 in Phase 2 to keep the schema-valid graph
deterministic. It is exposed as a module-level constant so Phase 5 can
enable it via configuration without changing call sites.
"""

from __future__ import annotations

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import DependencyType
from edutrace.utils.ids import PREFIX_DEPENDENCY, format_ids
from edutrace.utils.random_state import RandomStateManager

CROSS_COURSE_PREREQ_RATE: float = 0.0  # modelling assumption: disabled


def generate_curriculum_dependencies(
    config: EduTraceConfig,
    rng: RandomStateManager,
    modules: pl.DataFrame,
    courses: pl.DataFrame,
) -> pl.DataFrame:
    if modules.is_empty() or courses.is_empty():
        return _empty()

    mod = modules.sort(["course_id", "module_sequence"])
    course_ids = set(courses["course_id"].to_list())

    rows: list[dict] = []
    counter = 0

    # --- In-course sequence edges ---
    grouped = mod.group_by("course_id", maintain_order=True).agg(
        pl.col("module_id").sort_by("module_sequence").alias("module_ids")
    )
    for row in grouped.iter_rows(named=True):
        course_id = row["course_id"]
        module_ids = row["module_ids"]
        for k in range(1, len(module_ids)):
            counter += 1
            r = rng.row_rng("curriculum_dependency", counter)
            strength = float(r.beta(2.0, 3.0))  # tendency toward moderate
            rows.append(
                {
                    "dependency_id": format_ids(PREFIX_DEPENDENCY, [counter])[0],
                    "predecessor_module_id": module_ids[k - 1],
                    "successor_module_id": module_ids[k],
                    "dependency_type": DependencyType.PREREQUISITE.value,
                    "dependency_strength": strength,
                }
            )
            # Sanity: course_id is intentionally not stored; the schema has
            # no course_id column here. Assert that mapping is valid.
            assert course_id in course_ids

    # --- Cross-course prerequisites (disabled by default) ---
    if CROSS_COURSE_PREREQ_RATE > 0.0:
        r_global = rng.table_rng("curriculum_dependency")
        # Map course_id -> (semester, first module, last module).
        first_last = grouped.with_columns(
            pl.col("module_ids").list.first().alias("first_module"),
            pl.col("module_ids").list.last().alias("last_module"),
        ).join(
            courses.select("course_id", "programme_id", "semester"),
            on="course_id",
            how="inner",
        )

        for row in first_last.iter_rows(named=True):
            if r_global.random() >= CROSS_COURSE_PREREQ_RATE:
                continue
            course_id = row["course_id"]
            prog_id = row["programme_id"]
            semester = row["semester"]
            if semester <= 1:
                continue
            # Candidate predecessors: same programme, earlier semester.
            candidates = first_last.filter(
                (pl.col("programme_id") == prog_id)
                & (pl.col("semester") < semester)
            )
            if candidates.is_empty():
                continue
            pick = int(r_global.integers(0, candidates.height))
            pred = candidates.row(pick, named=True)

            counter += 1
            r = rng.row_rng("curriculum_dependency", counter)
            strength = float(r.beta(2.0, 3.0))
            rows.append(
                {
                    "dependency_id": format_ids(PREFIX_DEPENDENCY, [counter])[0],
                    "predecessor_module_id": pred["last_module"],
                    "successor_module_id": row["first_module"],
                    "dependency_type": DependencyType.PREREQUISITE.value,
                    "dependency_strength": strength,
                }
            )
            _ = course_id  # course_id only used for readability

    if not rows:
        return _empty()

    return pl.from_dicts(rows).with_columns(
        [
            pl.col("dependency_id").cast(pl.Utf8),
            pl.col("predecessor_module_id").cast(pl.Utf8),
            pl.col("successor_module_id").cast(pl.Utf8),
            pl.col("dependency_type").cast(pl.Utf8),
            pl.col("dependency_strength").cast(pl.Float64),
        ]
    )


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "dependency_id": pl.Utf8,
            "predecessor_module_id": pl.Utf8,
            "successor_module_id": pl.Utf8,
            "dependency_type": pl.Utf8,
            "dependency_strength": pl.Float64,
        }
    )
