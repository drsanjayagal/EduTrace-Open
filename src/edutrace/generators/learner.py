"""Learner generator.

Learners contain no real identifiers. Each learner is attached to a
programme and carries three latent traits used by later phases:

* ``baseline_preparedness`` — Beta(2, 2). Later phases use this as a factor
  in assessment performance.
* ``initial_engagement_profile`` — Beta(2, 2) slightly biased upward for
  full-time learners. Drives baseline weekly event count.
* ``synthetic_learning_preference`` — categorical over
  ``LEARNING_PREFERENCES`` with weights favouring video_first.

``synthetic_cohort_id`` groups learners by ``(admission_year, programme)``
so that later phases can reason about cohorts without inventing a new
table.

Admission year is drawn from ``[start_year, start_year + 2]`` where
``start_year`` is taken from ``academic_calendar_start``. Study mode is
categorical: full_time 70%, part_time 20%, online 10%. Entry pathway is
categorical over ``ENTRY_PATHWAYS`` with weights favouring
``standard_admission``.
"""

from __future__ import annotations

from datetime import date

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import (
    ENTRY_PATHWAYS,
    LEARNING_PREFERENCES,
    StudyMode,
)
from edutrace.utils.ids import PREFIX_LEARNER, format_ids
from edutrace.utils.random_state import RandomStateManager

_PREFERENCE_WEIGHTS = (0.45, 0.25, 0.20, 0.10)
_ENTRY_PATHWAY_WEIGHTS = (0.70, 0.10, 0.08, 0.07, 0.05)
_STUDY_MODE_VALUES = (
    StudyMode.FULL_TIME.value,
    StudyMode.PART_TIME.value,
    StudyMode.ONLINE.value,
)
_STUDY_MODE_WEIGHTS = (0.70, 0.20, 0.10)


def generate_learners(
    config: EduTraceConfig,
    rng: RandomStateManager,
    programmes: pl.DataFrame,
) -> pl.DataFrame:
    n = config.generation.num_learners
    if programmes.is_empty() or n <= 0:
        return _empty()

    prog_ids = programmes["programme_id"].to_list()
    # Uniform-ish distribution over programmes; slight preference for the
    # first programme to encourage cohort structure. Modelling assumption.
    weights = [1.0 / (i + 1) ** 0.3 for i in range(len(prog_ids))]
    total = sum(weights)
    prog_probs = [w / total for w in weights]

    start_year = _parse_year(config.generation.academic_calendar_start)
    cohort_range = (start_year, start_year + 2)  # inclusive
    weight_pref = _PREFERENCE_WEIGHTS
    weight_entry = _ENTRY_PATHWAY_WEIGHTS
    weight_mode = _STUDY_MODE_WEIGHTS

    rows: list[dict] = []
    for i in range(1, n + 1):
        r = rng.row_rng("learner", i)

        programme_id = str(r.choice(prog_ids, p=prog_probs))
        admission_year = int(r.integers(cohort_range[0], cohort_range[1] + 1))

        # Traits.
        preparedness = float(r.beta(2.0, 2.0))
        # Slight upward bias for full-time learners is applied below.
        study_mode = str(r.choice(_STUDY_MODE_VALUES, p=weight_mode))
        engagement_bias = 0.05 if study_mode == StudyMode.FULL_TIME.value else 0.0
        raw_engagement = float(r.beta(2.0, 2.0))
        engagement = float(min(1.0, max(0.0, raw_engagement + engagement_bias)))

        preference = str(r.choice(LEARNING_PREFERENCES, p=weight_pref))
        pathway = str(r.choice(ENTRY_PATHWAYS, p=weight_entry))

        cohort_id = f"coh_{admission_year}_{programme_id}"

        rows.append(
            {
                "learner_id": format_ids(PREFIX_LEARNER, [i])[0],
                "synthetic_cohort_id": cohort_id,
                "admission_year": admission_year,
                "entry_pathway": pathway,
                "study_mode": study_mode,
                "programme_id": programme_id,
                "baseline_preparedness": preparedness,
                "initial_engagement_profile": engagement,
                "synthetic_learning_preference": preference,
            }
        )

    return pl.from_dicts(rows).with_columns(
        [
            pl.col("learner_id").cast(pl.Utf8),
            pl.col("synthetic_cohort_id").cast(pl.Utf8),
            pl.col("admission_year").cast(pl.Int64),
            pl.col("entry_pathway").cast(pl.Utf8),
            pl.col("study_mode").cast(pl.Utf8),
            pl.col("programme_id").cast(pl.Utf8),
            pl.col("baseline_preparedness").cast(pl.Float64),
            pl.col("initial_engagement_profile").cast(pl.Float64),
            pl.col("synthetic_learning_preference").cast(pl.Utf8),
        ]
    )


def _parse_year(date_str: str) -> int:
    try:
        return date.fromisoformat(date_str).year
    except ValueError:
        # Fallback to a sensible synthetic anchor year.
        return 2023


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "learner_id": pl.Utf8,
            "synthetic_cohort_id": pl.Utf8,
            "admission_year": pl.Int64,
            "entry_pathway": pl.Utf8,
            "study_mode": pl.Utf8,
            "programme_id": pl.Utf8,
            "baseline_preparedness": pl.Float64,
            "initial_engagement_profile": pl.Float64,
            "synthetic_learning_preference": pl.Utf8,
        }
    )
