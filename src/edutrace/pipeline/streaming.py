"""Streaming spill-and-consolidate support for very large event tables."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

import polars as pl

from edutrace.exceptions import PipelineError
from edutrace.logging_config import get_logger
from edutrace.pipeline.checkpoint import CheckpointManager
from edutrace.utils.file_utils import ensure_dir

_log = get_logger(__name__)


class SpillManager:
    """Write per-chunk Parquet files and read them back."""

    def __init__(
        self,
        checkpoint: CheckpointManager,
        *,
        compression: str = "zstd",
        row_group_size: int = 200_000,
    ) -> None:
        self.checkpoint = checkpoint
        self.root = ensure_dir(Path(checkpoint.directory) / "spill")
        self.compression = compression
        self.row_group_size = row_group_size

    def chunk_path(self, table: str, chunk_idx: int) -> Path:
        return self.root / f"{table}_chunk_{chunk_idx:07d}.parquet"

    def write_chunk(self, table: str, chunk_idx: int, df: pl.DataFrame) -> Path:
        path = self.chunk_path(table, chunk_idx)
        df.write_parquet(
            path,
            compression=self.compression,
            row_group_size=self.row_group_size,
        )
        self.checkpoint.set_last_chunk(table, chunk_idx)
        _log.debug(
            "Spilled %s chunk %d (%d rows) → %s",
            table,
            chunk_idx,
            df.height,
            path,
        )
        return path

    def has_chunk(self, table: str, chunk_idx: int) -> bool:
        return self.chunk_path(table, chunk_idx).exists()

    def read_chunk(self, table: str, chunk_idx: int) -> pl.DataFrame:
        path = self.chunk_path(table, chunk_idx)
        if not path.exists():
            raise PipelineError(f"Missing spill chunk: {path}")
        return pl.read_parquet(path)

    def scan_all(self, table: str) -> pl.LazyFrame:
        """Return a LazyFrame over all spilled chunks for ``table``."""
        paths = sorted(self.root.glob(f"{table}_chunk_*.parquet"))
        if not paths:
            raise PipelineError(f"No spilled chunks for {table}")
        return pl.scan_parquet(paths)

    def consolidate(
        self,
        table: str,
        destination: Path,
        *,
        row_group_size: int | None = None,
        empty_schema: dict[str, Any] | None = None,
    ) -> int:
        """Write all spilled chunks to ``destination`` as one Parquet file."""
        paths = sorted(self.root.glob(f"{table}_chunk_*.parquet"))
        if not paths:
            if empty_schema is None:
                raise PipelineError(
                    f"No spilled chunks to consolidate for {table}"
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            pl.DataFrame(schema=empty_schema).write_parquet(
                destination,
                compression=self.compression,
                row_group_size=row_group_size or self.row_group_size,
            )
            _log.info(
                "Wrote empty schema-only parquet for %s → %s", table, destination
            )
            return 0

        lf = pl.scan_parquet(paths)
        row_count = int(lf.select(pl.len()).collect().item())
        lf.sink_parquet(
            destination,
            compression=self.compression,
            row_group_size=row_group_size or self.row_group_size,
        )
        _log.info(
            "Consolidated %s: %d rows from %d chunks → %s",
            table,
            row_count,
            len(paths),
            destination,
        )
        return row_count

    def cleanup(self) -> None:
        """Delete all spill files. Called after a successful run."""
        if not self.root.exists():
            return
        for f in self.root.glob("*.parquet"):
            with contextlib.suppress(OSError):
                f.unlink()
