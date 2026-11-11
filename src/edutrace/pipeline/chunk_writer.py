"""Table writer for Parquet, CSV, and JSONL output.

Each table is written to exactly one output file. Directory layout mirrors
the spec:

    <root>/<category>/<table>.parquet
    <root>/<category>/<table>.csv
    <root>/<category>/<table>.jsonl       (learning_event only, by default)

Categories are declared in ``_TABLE_CATEGORY``. This mapping is used by
both the writer and the manifest.

CSV columns are written as-is (Polars' default formatting), which
round-trips correctly for the dtypes used in this project (strings, int64,
float64, bool, datetime[us]).

Parquet uses Zstandard compression and the configured row-group size.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from edutrace.config import EduTraceConfig, OutputFormat
from edutrace.exceptions import ExportError
from edutrace.logging_config import get_logger
from edutrace.utils.file_utils import ensure_dir

_log = get_logger(__name__)

_TABLE_CATEGORY: dict[str, str] = {
    "institution": "institutional",
    "programme": "institutional",
    "course": "academic",
    "module": "academic",
    "curriculum_dependency": "academic",
    "learner": "learners",
    "enrolment": "learners",
    "progression_event": "learners",
    "learning_resource": "learning",
    "learning_event": "learning",
    "weekly_engagement": "learning",
    "assessment_item": "assessment",
    "assessment_attempt": "assessment",
    "feedback_event": "assessment",
    "digital_access": "accessibility",
    "support_event": "interventions",
}

# Per-format extension.
_EXT: dict[OutputFormat, str] = {
    "parquet": "parquet",
    "csv": "csv",
    "jsonl": "jsonl",
}


class ChunkWriter:
    """One writer per pipeline run. Accumulates a file list."""

    def __init__(self, config: EduTraceConfig) -> None:
        self.config = config
        self.root = ensure_dir(config.output.directory)
        self.formats = list(config.output.formats)
        self.written_files: list[Path] = []

    def category_of(self, table: str) -> str:
        try:
            return _TABLE_CATEGORY[table]
        except KeyError as exc:
            raise ExportError(f"Unknown table for output: {table!r}") from exc

    def path_for(self, table: str, fmt: OutputFormat) -> Path:
        category = self.category_of(table)
        directory = ensure_dir(self.root / category)
        return directory / f"{table}.{_EXT[fmt]}"

    def write_table(self, table: str, df: pl.DataFrame) -> list[Path]:
        if df is None:
            raise ExportError(f"Cannot write {table}: got None")
        written: list[Path] = []
        for fmt in self.formats:
            path = self.path_for(table, fmt)
            try:
                self._write_one(df, path, fmt)
            except Exception as exc:
                raise ExportError(f"Failed to write {table} → {path}: {exc}") from exc
            written.append(path)
            self.written_files.append(path)
            _log.info("Wrote %s (%d rows) → %s", table, df.height, path)
        return written

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _write_one(self, df: pl.DataFrame, path: Path, fmt: OutputFormat) -> None:
        if fmt == "parquet":
            df.write_parquet(
                path,
                compression=self.config.output.compression,
                row_group_size=self.config.output.row_group_size,
            )
        elif fmt == "csv":
            df.write_csv(path)
        elif fmt == "jsonl":
            df.write_ndjson(path)
        else:
            raise ExportError(f"Unsupported format: {fmt}")
