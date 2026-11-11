"""Institution generator.

Design
------
Institutions are the roots of the academic tree. All other tables derive
from them. The number of institutions is ``config.generation.num_institutions``.

Every institution gets:
* a type drawn from ``INSTITUTION_TYPES``
* a country (currently ``"IN"``, synthetic only)
* a region drawn from ``REGIONS``
* a free-form ``academic_calendar`` string built from the config
* a timezone from the project config

IDs are ``inst_<N>`` with N starting at 1.
"""

from __future__ import annotations

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import (
    COUNTRIES,
    INSTITUTION_TYPES,
    REGIONS,
)
from edutrace.utils.ids import PREFIX_INSTITUTION, format_ids
from edutrace.utils.random_state import RandomStateManager

_INSTITUTION_TYPE_WEIGHTS = (0.35, 0.25, 0.15, 0.25)  # sums to 1.0
_REGION_WEIGHTS = (0.20, 0.25, 0.20, 0.20, 0.15)


def generate_institutions(
    config: EduTraceConfig,
    rng: RandomStateManager,
) -> pl.DataFrame:
    """Return one row per institution."""
    n = config.generation.num_institutions

    # Single table-scoped RNG is fine here: no per-row stochasticity that
    # needs to survive chunk boundaries, because institutions are always
    # generated as a single block.
    g = rng.table_rng("institution")

    calendar_desc = (
        f"{config.generation.semesters_per_year} semesters/year, "
        f"{config.generation.weeks_per_semester} weeks/semester, "
        f"start {config.generation.academic_calendar_start}"
    )

    types = g.choice(
        INSTITUTION_TYPES, size=n, p=_INSTITUTION_TYPE_WEIGHTS
    ).tolist()
    regions = g.choice(REGIONS, size=n, p=_REGION_WEIGHTS).tolist()
    country = COUNTRIES[0]

    df = pl.DataFrame(
        {
            "institution_id": format_ids(PREFIX_INSTITUTION, list(range(1, n + 1))),
            "institution_type": types,
            "country": [country] * n,
            "region": regions,
            "academic_calendar": [calendar_desc] * n,
            "timezone": [config.project.timezone] * n,
        }
    ).with_columns(
        [
            pl.col("institution_id").cast(pl.Utf8),
            pl.col("institution_type").cast(pl.Utf8),
            pl.col("country").cast(pl.Utf8),
            pl.col("region").cast(pl.Utf8),
            pl.col("academic_calendar").cast(pl.Utf8),
            pl.col("timezone").cast(pl.Utf8),
        ]
    )

    return df
