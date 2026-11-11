"""Descriptive summaries used by ``inspect`` and by downstream analyses."""

from __future__ import annotations

import polars as pl


def column_summary(df: pl.DataFrame) -> pl.DataFrame:
    """One row per column: dtype, nulls, distinct, min/mean/max for numerics."""
    rows: list[dict] = []
    for col_name, dtype in df.schema.items():
        s = df[col_name]
        row: dict = {
            "column": col_name,
            "dtype": str(dtype),
            "null_count": int(s.null_count()),
            "distinct": int(s.n_unique()),
        }
        if isinstance(dtype, (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                              pl.Float32, pl.Float64)):
            nn = s.drop_nulls()
            if not nn.is_empty():
                row.update(
                    min=float(nn.min()),
                    mean=float(nn.mean()),
                    max=float(nn.max()),
                )
        rows.append(row)
    return pl.from_dicts(rows)


def table_sizes(tables: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Row and column counts for each table."""
    return pl.from_dicts(
        [
            {"table": name, "rows": int(df.height), "columns": int(df.width)}
            for name, df in sorted(tables.items())
        ]
    )


def categorical_distribution(
    df: pl.DataFrame, column: str, *, top: int = 20
) -> pl.DataFrame:
    """Return the top-N values of a categorical column with counts."""
    if column not in df.columns:
        raise KeyError(f"Column {column!r} not in DataFrame")
    return (
        df[column]
        .value_counts()
        .sort("count", descending=True)
        .head(top)
    )
