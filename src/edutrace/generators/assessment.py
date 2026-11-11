"""Assessment-item generator.

Items are attached to modules. Each module gets
``assessment_items_per_module`` items with a categorical type mix
(``ASSESSMENT_TYPE_WEIGHTS``). Per-module weights are normalised to 1.0.

Item-level difficulty is derived from module difficulty with a small
positive bias for exams. ``learning_objective_id`` is a synthetic string
of the form ``LO_<module>_<n>``; it is *not* a foreign key to a real LO
table — the module's learning_objectives field holds free text.

Attempt generation is Phase 4. This module only produces the item table.
"""

from __future__ import annotations

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import ASSESSMENT_TYPE_WEIGHTS
from edutrace.utils.ids import PREFIX_ASSESSMENT_ITEM, format_ids
from edutrace.utils.random_state import RandomStateManager


def generate_assessment_items(
    config: EduTraceConfig,
    rng: RandomStateManager,
    modules: pl.DataFrame,
) -> pl.DataFrame:
    n_per = config.generation.assessment_items_per_module
    if modules.is_empty() or n_per <= 0:
        return _empty()

    type_labels = tuple(ASSESSMENT_TYPE_WEIGHTS.keys())
    type_probs = [ASSESSMENT_TYPE_WEIGHTS[t] for t in type_labels]
    total = sum(type_probs)
    type_probs = [p / total for p in type_probs]

    rows: list[dict] = []
    counter = 0

    for mod_row in modules.iter_rows(named=True):
        module_id = mod_row["module_id"]
        course_id = mod_row["course_id"]
        module_difficulty = _module_difficulty_proxy(mod_row)

        # Draw all items for this module first so weights can be normalised.
        raw_items: list[dict] = []
        for k in range(1, n_per + 1):
            counter += 1
            r = rng.row_rng("assessment_item", counter)
            atype = str(r.choice(type_labels, p=type_probs))
            raw_weight = float(max(0.1, r.gamma(2.0, 0.6)))
            jitter = float(r.normal(0.0, 0.05))
            difficulty = float(min(1.0, max(0.0, module_difficulty + jitter)))
            if atype == "exam":
                difficulty = float(min(1.0, difficulty + 0.10))
            max_score = 10.0 if atype == "formative_check" else 100.0
            raw_items.append(
                {
                    "assessment_item_id": format_ids(PREFIX_ASSESSMENT_ITEM, [counter])[0],
                    "course_id": course_id,
                    "module_id": module_id,
                    "assessment_type": atype,
                    "difficulty": difficulty,
                    "maximum_score": max_score,
                    "raw_weight": raw_weight,
                    "learning_objective_id": f"LO_{module_id}_{k}",
                }
            )

        weight_sum = sum(it["raw_weight"] for it in raw_items)
        for it in raw_items:
            it["weight"] = float(it["raw_weight"] / weight_sum)
            del it["raw_weight"]
            rows.append(it)

    if not rows:
        return _empty()

    return pl.from_dicts(rows).with_columns(
        [
            pl.col("assessment_item_id").cast(pl.Utf8),
            pl.col("course_id").cast(pl.Utf8),
            pl.col("module_id").cast(pl.Utf8),
            pl.col("assessment_type").cast(pl.Utf8),
            pl.col("difficulty").cast(pl.Float64),
            pl.col("maximum_score").cast(pl.Float64),
            pl.col("weight").cast(pl.Float64),
            pl.col("learning_objective_id").cast(pl.Utf8),
        ]
    )


def _module_difficulty_proxy(mod_row: dict) -> float:
    """Return a [0,1] difficulty proxy for a module.

    Module rows do not carry a ``difficulty_level`` column, so we proxy via
    ``estimated_learning_hours`` using the same logistic used for
    resources. Consistency with ``resource.py`` is intentional.
    """
    x = (float(mod_row["estimated_learning_hours"]) - 15.0) / 12.0
    return float(1.0 / (1.0 + pow(2.718281828, -x)))


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "assessment_item_id": pl.Utf8,
            "course_id": pl.Utf8,
            "module_id": pl.Utf8,
            "assessment_type": pl.Utf8,
            "difficulty": pl.Float64,
            "maximum_score": pl.Float64,
            "weight": pl.Float64,
            "learning_objective_id": pl.Utf8,
        }
    )
