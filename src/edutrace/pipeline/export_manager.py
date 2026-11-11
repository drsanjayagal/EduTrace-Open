"""Format-conversion utilities for existing outputs.

``export_formats`` reads a dataset directory (as written by the pipeline)
and produces additional format files for the same tables, without
regenerating any data.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from edutrace.config import OutputFormat
from edutrace.exceptions import ExportError
from edutrace.logging_config import get_logger

_log = get_logger(__name__)


def export_formats(
    input_dir: str | Path,
    formats: list[OutputFormat],
    *,
    compression: str = "zstd",
    row_group_size: int = 200_000,
) -> list[Path]:
    """Read every ``*.parquet`` under ``input_dir`` and write ``formats``.

    CSV and JSONL outputs are written alongside the Parquet source, in the
    same directory. A ``parquet`` target re-writes the Parquet source with
    the requested ``compression`` and ``row_group_size``.
    """
    root = Path(input_dir)
    if not root.is_dir():
        raise ExportError(f"Input directory not found: {root}")

    written: list[Path] = []
    for src in sorted(root.rglob("*.parquet")):
        df = pl.read_parquet(src)
        for fmt in formats:
            if fmt == "parquet":
                dst = src.with_name(src.stem + ".parquet")
                df.write_parquet(
                    dst,
                    compression=compression,
                    row_group_size=row_group_size,
                )
            elif fmt == "csv":
                dst = src.with_suffix(".csv")
                df.write_csv(dst)
            elif fmt == "jsonl":
                dst = src.with_suffix(".jsonl")
                df.write_ndjson(dst)
            else:
                raise ExportError(f"Unsupported export format: {fmt}")
            written.append(dst)
            _log.info("Exported %s → %s", src.stem, dst)

    return written
