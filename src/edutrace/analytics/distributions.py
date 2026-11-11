"""Distribution summaries for the CLI and notebooks."""

from __future__ import annotations

import polars as pl


def histogram(
    df: pl.DataFrame,
    column: str,
    *,
    bins: int = 20,
) -> pl.DataFrame:
    """Return a histogram of a numeric column as ``(bin_left, count)``."""
    if column not in df.columns:
        raise KeyError(f"Column {column!r} not in DataFrame")
    s = df[column].drop_nulls()
    if s.is_empty():
        return pl.DataFrame(schema={"bin_left": pl.Float64, "count": pl.Int64})
    lo = float(s.min())
    hi = float(s.max())
    if hi == lo:
        return pl.DataFrame({"bin_left": [lo], "count": [int(s.len())]})
    width = (hi - lo) / bins
    edges = [lo + i * width for i in range(bins)] + [hi + 1e-9]
    counts = [0] * bins
    for v in s.to_list():
        idx = min(bins - 1, max(0, int((v - lo) / width)))
        counts[idx] += 1
    return pl.DataFrame(
        {"bin_left": edges[:-1], "count": counts}
    )


def score_distribution(
    attempts: pl.DataFrame, *, bins: int = 20
) -> pl.DataFrame:
    """Histogram of attempt score fractions in [0, 1]."""
    fractions = attempts.select(
        (pl.col("score") / pl.col("maximum_score")).alias("fraction")
    )
    return histogram(fractions, "fraction", bins=bins)
