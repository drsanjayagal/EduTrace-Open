"""Correlation analyses between numeric columns."""

from __future__ import annotations

import polars as pl


def numeric_correlation(
    df: pl.DataFrame, *, columns: list[str] | None = None
) -> pl.DataFrame:
    """Return a Pearson correlation matrix over numeric columns.

    If ``columns`` is provided, only those columns are considered (a
    ``KeyError`` is raised if any is missing).
    """
    numeric = [
        c for c, t in df.schema.items()
        if isinstance(t, (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                          pl.Float32, pl.Float64))
    ]
    if columns is not None:
        for c in columns:
            if c not in numeric:
                raise KeyError(f"Column {c!r} is not numeric")
        numeric = columns

    if not numeric:
        return pl.DataFrame()

    corr = df.select(numeric).drop_nulls().corr()
    # Polars returns a frame where the first column is named "column" and
    # subsequent columns share names with numeric inputs. We reshape to
    # long form for convenience.
    long_rows: list[dict] = []
    for row in corr.iter_rows(named=True):
        for other in numeric:
            if row.get(other) is not None and row.get("column") != other:
                long_rows.append(
                    {
                        "col_a": row["column"],
                        "col_b": other,
                        "pearson_r": float(row[other]),
                    }
                )
    return pl.from_dicts(long_rows)


def correlation_between(
    left_df: pl.DataFrame, left_col: str,
    right_df: pl.DataFrame, right_col: str,
    join_on: str,
) -> float:
    """Correlation between two columns joined on a shared key."""
    joined = left_df.select(join_on, left_col).join(
        right_df.select(join_on, right_col), on=join_on, how="inner"
    ).drop_nulls()
    if joined.height < 2:
        return 0.0
    corr = joined.select(
        pl.corr(pl.col(left_col), pl.col(right_col)).alias("r")
    ).item()
    return float(corr) if corr is not None else 0.0
