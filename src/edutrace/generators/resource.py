"""Learning-resource generator.

Every module gets ``config.generation.resources_per_module`` resources.
Resource types follow a fixed categorical mix (see ``RESOURCE_TYPE_WEIGHTS``
in constants). Formats are constrained by type.

``accessibility_features`` is a synthetic semicolon-joined string of feature
flags (caption, transcript, alt_text, screen_reader_ready). These are
*simulated availability flags*, not claims about any real content.

``publication_sequence`` runs 1..N per module.
"""

from __future__ import annotations

import math

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import (
    RESOURCE_FORMAT_BY_TYPE,
    RESOURCE_TYPE_WEIGHTS,
)
from edutrace.utils.ids import PREFIX_RESOURCE, format_ids
from edutrace.utils.random_state import RandomStateManager


def generate_resources(
    config: EduTraceConfig,
    rng: RandomStateManager,
    modules: pl.DataFrame,
) -> pl.DataFrame:
    n_per = config.generation.resources_per_module
    if modules.is_empty() or n_per <= 0:
        return _empty()

    type_labels = tuple(RESOURCE_TYPE_WEIGHTS.keys())
    type_probs = [RESOURCE_TYPE_WEIGHTS[t] for t in type_labels]
    total = sum(type_probs)
    type_probs = [p / total for p in type_probs]

    rows: list[dict] = []
    counter = 0

    for mod_row in modules.iter_rows(named=True):
        module_id = mod_row["module_id"]
        course_id = mod_row["course_id"]
        mod_hours = float(mod_row["estimated_learning_hours"])
        module_difficulty = _difficulty_from_hours(mod_hours)

        for seq in range(1, n_per + 1):
            counter += 1
            r = rng.row_rng("learning_resource", counter)

            rtype = str(r.choice(type_labels, p=type_probs))
            formats = RESOURCE_FORMAT_BY_TYPE[rtype]
            rformat = formats[0] if len(formats) == 1 else str(r.choice(formats))

            jitter = float(r.normal(0.0, 0.05))
            difficulty = float(min(1.0, max(0.0, module_difficulty + jitter)))

            base_duration = float(r.gamma(2.0, 8.0))  # minutes
            if rtype == "lecture_video":
                base_duration *= 2.5
            elif rtype == "quiz":
                base_duration *= 1.5
            duration = round(base_duration, 2)

            features: list[str] = []
            if r.random() < 0.55:
                features.append("caption")
            if r.random() < 0.45:
                features.append("transcript")
            if r.random() < 0.35:
                features.append("alt_text")
            if r.random() < 0.20:
                features.append("screen_reader_ready")
            accessibility = ";".join(features) if features else "none"

            rows.append(
                {
                    "resource_id": format_ids(PREFIX_RESOURCE, [counter])[0],
                    "course_id": course_id,
                    "module_id": module_id,
                    "resource_type": rtype,
                    "resource_format": rformat,
                    "difficulty_level": difficulty,
                    "estimated_duration": duration,
                    "accessibility_features": accessibility,
                    "publication_sequence": seq,
                }
            )

    if not rows:
        return _empty()

    return pl.from_dicts(rows).with_columns(
        [
            pl.col("resource_id").cast(pl.Utf8),
            pl.col("course_id").cast(pl.Utf8),
            pl.col("module_id").cast(pl.Utf8),
            pl.col("resource_type").cast(pl.Utf8),
            pl.col("resource_format").cast(pl.Utf8),
            pl.col("difficulty_level").cast(pl.Float64),
            pl.col("estimated_duration").cast(pl.Float64),
            pl.col("accessibility_features").cast(pl.Utf8),
            pl.col("publication_sequence").cast(pl.Int64),
        ]
    )


def _difficulty_from_hours(est_hours: float) -> float:
    """Map estimated_learning_hours (Gamma-shaped, usually 4-40) to [0, 1].

    Uses a logistic-style squash with midpoint at 15 hours.
    Modelling assumption: longer modules are somewhat harder.
    """
    x = (est_hours - 15.0) / 12.0
    return float(1.0 / (1.0 + math.exp(-x)))


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "resource_id": pl.Utf8,
            "course_id": pl.Utf8,
            "module_id": pl.Utf8,
            "resource_type": pl.Utf8,
            "resource_format": pl.Utf8,
            "difficulty_level": pl.Float64,
            "estimated_duration": pl.Float64,
            "accessibility_features": pl.Utf8,
            "publication_sequence": pl.Int64,
        }
    )
