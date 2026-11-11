"""Digital-access generator.

One row per learner *per academic year*. Categories are drawn from weighted
categoricals; reliability is a weighted combination of categories plus
noise, clipped to [0, 1]; constraint level is derived from reliability
thresholds.

We deliberately avoid any demographic linkage. Access conditions are
synthetic and independent of any protected attribute — a validation
requirement enforced by the *absence* of such attributes in the learner
schema.

Row-key note
------------
The deterministic RNG seed for each (learner, academic year) record is
derived from ``row_key_from_ints(learner_num, year_offset, 0, 0)``. We use
``year_offset`` (0..num_academic_years-1) rather than the absolute
``academic_year`` (2026, 2027, …) because the year is intrinsically a
small offset from admission and does not need to be encoded in the key.
Using the offset also keeps the key well under the positional bounds
regardless of how far in the future the calendar start lies.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.constants import (
    ACCESS_CONSTRAINT_THRESHOLDS,
    ACCESS_RELIABILITY_WEIGHTS,
    BANDWIDTH_CATEGORY_WEIGHTS,
    CONNECTIVITY_CATEGORY_WEIGHTS,
    DEVICE_CATEGORY_WEIGHTS,
)
from edutrace.utils.ids import (
    PREFIX_ACCESS,
    format_id,
    parse_id,
    row_key_from_ints,
)
from edutrace.utils.random_state import RandomStateManager


def generate_digital_access(
    config: EduTraceConfig,
    rng: RandomStateManager,
    learners: pl.DataFrame,
    *,
    access_id_start: int = 1,
) -> tuple[pl.DataFrame, int]:
    """Return ``(digital_access_df, next_access_id_start)``."""
    if learners.is_empty():
        return _empty(), access_id_start

    device_labels = tuple(DEVICE_CATEGORY_WEIGHTS.keys())
    device_probs = np.array(list(DEVICE_CATEGORY_WEIGHTS.values()))
    device_probs = device_probs / device_probs.sum()

    conn_labels = tuple(CONNECTIVITY_CATEGORY_WEIGHTS.keys())
    conn_probs = np.array(list(CONNECTIVITY_CATEGORY_WEIGHTS.values()))
    conn_probs = conn_probs / conn_probs.sum()

    bw_labels = tuple(BANDWIDTH_CATEGORY_WEIGHTS.keys())
    bw_probs = np.array(list(BANDWIDTH_CATEGORY_WEIGHTS.values()))
    bw_probs = bw_probs / bw_probs.sum()

    rows: list[dict] = []
    counter = access_id_start

    for learner_row in learners.iter_rows(named=True):
        learner_id = learner_row["learner_id"]
        learner_num = parse_id(learner_id)[1]
        admission_year = int(learner_row["admission_year"])

        for year_offset in range(config.generation.num_academic_years):
            academic_year = admission_year + year_offset
            # Row key uses the per-learner year offset (0..N-1), not the
            # absolute academic year. Deterministic, and bounded by
            # num_academic_years (<= 10) rather than by the calendar year.
            key = row_key_from_ints(learner_num, year_offset, 0, 0)
            r = rng.row_rng("digital_access", key)

            device = str(r.choice(device_labels, p=device_probs))
            connectivity = str(r.choice(conn_labels, p=conn_probs))
            bandwidth = str(r.choice(bw_labels, p=bw_probs))

            components = [
                ACCESS_RELIABILITY_WEIGHTS[device],
                ACCESS_RELIABILITY_WEIGHTS[connectivity],
                ACCESS_RELIABILITY_WEIGHTS[f"{bandwidth}_bandwidth"],
            ]
            reliability_raw = float(np.mean(components))
            reliability = float(
                np.clip(reliability_raw + r.normal(0.0, 0.05), 0.0, 1.0)
            )

            constraint = "none"
            for label, upper in ACCESS_CONSTRAINT_THRESHOLDS:
                if reliability <= upper:
                    constraint = label
                    break

            offline = float(
                np.clip(1.0 - reliability + r.normal(0.0, 0.05), 0.0, 1.0)
            )
            access_support = bool(r.random() < 0.10 + 0.30 * (1.0 - reliability))

            rows.append(
                {
                    "access_record_id": format_id(PREFIX_ACCESS, counter),
                    "learner_id": learner_id,
                    "observation_period": f"AY{academic_year}",
                    "device_category": device,
                    "connectivity_category": connectivity,
                    "bandwidth_category": bandwidth,
                    "access_reliability": round(reliability, 4),
                    "offline_access_usage": round(offline, 4),
                    "accessibility_support_usage": access_support,
                    "access_constraint_level": constraint,
                }
            )
            counter += 1

    if not rows:
        return _empty(), counter

    df = pl.from_dicts(rows, infer_schema_length=len(rows)).with_columns(
        [
            pl.col("access_record_id").cast(pl.Utf8),
            pl.col("learner_id").cast(pl.Utf8),
            pl.col("observation_period").cast(pl.Utf8),
            pl.col("device_category").cast(pl.Utf8),
            pl.col("connectivity_category").cast(pl.Utf8),
            pl.col("bandwidth_category").cast(pl.Utf8),
            pl.col("access_reliability").cast(pl.Float64),
            pl.col("offline_access_usage").cast(pl.Float64),
            pl.col("accessibility_support_usage").cast(pl.Boolean),
            pl.col("access_constraint_level").cast(pl.Utf8),
        ]
    )
    return df, counter


def _empty() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "access_record_id": pl.Utf8,
            "learner_id": pl.Utf8,
            "observation_period": pl.Utf8,
            "device_category": pl.Utf8,
            "connectivity_category": pl.Utf8,
            "bandwidth_category": pl.Utf8,
            "access_reliability": pl.Float64,
            "offline_access_usage": pl.Float64,
            "accessibility_support_usage": pl.Boolean,
            "access_constraint_level": pl.Utf8,
        }
    )
