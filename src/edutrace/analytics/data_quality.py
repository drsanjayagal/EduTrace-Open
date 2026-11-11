"""Data-quality reports: completeness, referential sanity, consistency."""

from __future__ import annotations

import polars as pl


def completeness(df: pl.DataFrame) -> pl.DataFrame:
    """Return non-null fraction per column."""
    rows = []
    n = df.height
    for col in df.columns:
        non_null = int(df[col].is_not_null().sum())
        fraction = non_null / n if n else 0.0
        rows.append(
            {"column": col, "non_null": non_null, "non_null_fraction": fraction}
        )
    return pl.from_dicts(rows)


def duplicate_primary_key_check(df: pl.DataFrame, key: str) -> int:
    """Return the number of duplicate rows on ``key``; 0 means clean."""
    if key not in df.columns:
        raise KeyError(f"Key column {key!r} not in DataFrame")
    return int(df[key].is_duplicated().sum())


def orphan_check(
    child: pl.DataFrame, child_col: str,
    parent: pl.DataFrame, parent_col: str,
) -> int:
    """Return the number of orphaned child values."""
    child_vals = child.filter(pl.col(child_col).is_not_null()).select(
        pl.col(child_col).alias("_k")
    )
    parent_vals = parent.select(pl.col(parent_col).alias("_k")).unique()
    orphans = child_vals.join(parent_vals, on="_k", how="anti")
    return int(orphans.height)
