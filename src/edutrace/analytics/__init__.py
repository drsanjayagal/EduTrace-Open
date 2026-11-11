"""Analytics subpackage.

The Phase-9 loader and summariser remain here for compatibility; the
Phase-10 modules add descriptive, correlation, trajectory, distribution,
and data-quality helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from edutrace.analytics import (
    correlation,
    data_quality,
    descriptive,
    distributions,
    trajectories,
)


def summarise_tables(
    tables: dict[str, pl.DataFrame],
    *,
    max_categorical: int = 6,
) -> dict[str, Any]:
    """JSON-safe descriptive summary of every table."""
    summary: dict[str, Any] = {}
    for name, df in sorted(tables.items()):
        summary[name] = _summarise_one(df, max_categorical=max_categorical)
    return summary


def _summarise_one(df: pl.DataFrame, *, max_categorical: int) -> dict[str, Any]:
    out: dict[str, Any] = {
        "row_count": int(df.height),
        "column_count": int(df.width),
        "columns": {},
    }
    for col_name, dtype in df.schema.items():
        col = df[col_name]
        info: dict[str, Any] = {
            "dtype": str(dtype),
            "null_count": int(col.null_count()),
        }
        if isinstance(dtype, (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                              pl.Float32, pl.Float64)):
            s = col.drop_nulls()
            if s.is_empty():
                info.update({"kind": "numeric", "empty": True})
            else:
                info.update(
                    kind="numeric",
                    min=float(s.min()),
                    max=float(s.max()),
                    mean=float(s.mean()),
                    std=float(s.std()) if s.len() > 1 else 0.0,
                )
        elif isinstance(dtype, pl.Boolean):
            info.update(kind="boolean", true_count=int(col.sum()))
        elif isinstance(dtype, pl.Datetime):
            s = col.drop_nulls()
            if s.is_empty():
                info.update({"kind": "datetime", "empty": True})
            else:
                info.update(kind="datetime", min=str(s.min()), max=str(s.max()))
        else:
            s = col.drop_nulls()
            if s.is_empty():
                info.update({"kind": "string", "empty": True})
            else:
                counts = (
                    s.value_counts()
                    .sort("count", descending=True)
                    .head(max_categorical)
                )
                info.update(
                    kind="string",
                    distinct=int(s.n_unique()),
                    top=[
                        {"value": str(r[col_name]), "count": int(r["count"])}
                        for r in counts.iter_rows(named=True)
                    ],
                )
        out["columns"][col_name] = info
    return out


def load_dataset_from_disk(root: str | Path) -> dict[str, pl.DataFrame]:
    """Load every ``*.parquet`` under ``root`` keyed by file stem."""
    root_p = Path(root)
    if not root_p.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {root_p}")
    out: dict[str, pl.DataFrame] = {}
    for path in sorted(root_p.rglob("*.parquet")):
        if "manifests" in path.parts or "validation" in path.parts:
            continue
        out[path.stem] = pl.read_parquet(path)
    return out


__all__ = [
    "correlation",
    "data_quality",
    "descriptive",
    "distributions",
    "load_dataset_from_disk",
    "summarise_tables",
    "trajectories",
]
