"""Checkpoint manager.

The checkpoint file is a small JSON document containing:

* ``config_sha256`` — SHA-256 of the canonicalised config.
* ``seed`` — the random seed.
* ``completed_tables`` — list of table names that have been fully written.
* ``chunk_progress`` — mapping ``table -> last completed chunk index``.
* ``next_ids`` — mapping ``table -> next id counter value``.
* ``chunk_files`` — mapping ``table -> [spilled chunk paths]``.

The orchestrator calls :meth:`CheckpointManager.save` at safe boundaries.
It calls :meth:`CheckpointManager.load` on startup.

Notes on private keys
---------------------
Some orchestrator stages (e.g. ``_enrolment_outcomes``) are not real
tables in ``ALL_TABLES``; they are *modifications* to an existing table.
The orchestrator records them under names beginning with ``_`` so that
resume logic can distinguish them from schema tables. These names are not
part of the public API and may change between versions.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from edutrace.config import EduTraceConfig, dump_config
from edutrace.exceptions import CheckpointError
from edutrace.logging_config import get_logger
from edutrace.utils.file_utils import ensure_dir
from edutrace.utils.hashing import sha256_bytes

_log = get_logger(__name__)


@dataclass
class CheckpointState:
    config_sha256: str = ""
    seed: int = 0
    completed_tables: list[str] = field(default_factory=list)
    chunk_progress: dict[str, int] = field(default_factory=dict)
    next_ids: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    chunk_files: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_sha256": self.config_sha256,
            "seed": self.seed,
            "completed_tables": list(self.completed_tables),
            "chunk_progress": dict(self.chunk_progress),
            "next_ids": dict(self.next_ids),
            "notes": list(self.notes),
            "chunk_files": {k: list(v) for k, v in self.chunk_files.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckpointState:
        return cls(
            config_sha256=str(data.get("config_sha256", "")),
            seed=int(data.get("seed", 0)),
            completed_tables=list(data.get("completed_tables", [])),
            chunk_progress=dict(data.get("chunk_progress", {})),
            next_ids=dict(data.get("next_ids", {})),
            notes=list(data.get("notes", [])),
            chunk_files={
                str(k): [str(p) for p in v]
                for k, v in dict(data.get("chunk_files", {})).items()
            },
        )


def config_sha256(config: EduTraceConfig) -> str:
    """Stable SHA-256 of a canonicalised config dict."""
    data = dump_config(config)
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return sha256_bytes(canonical)


class CheckpointManager:
    """Persist and restore orchestrator state."""

    FILENAME = "state.json"

    def __init__(self, directory: str | Path, config: EduTraceConfig) -> None:
        self.directory = ensure_dir(directory)
        self.path = self.directory / self.FILENAME
        self.config = config
        self._state = self._load_or_init()
        self._checkpoint_enabled = config.pipeline.checkpoint.enabled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> CheckpointState:
        return self._state

    def is_completed(self, table: str) -> bool:
        return table in self._state.completed_tables

    def mark_completed(self, table: str) -> None:
        if table not in self._state.completed_tables:
            self._state.completed_tables.append(table)
            self.save()

    def next_id(self, table: str, default: int = 1) -> int:
        return self._state.next_ids.get(table, default)

    def set_next_id(self, table: str, value: int) -> None:
        self._state.next_ids[table] = value
        self.save()

    def last_chunk(self, table: str) -> int:
        return self._state.chunk_progress.get(table, -1)

    def set_last_chunk(self, table: str, chunk_idx: int) -> None:
        self._state.chunk_progress[table] = chunk_idx
        self.save()

    def record_chunk_file(self, table: str, path: str) -> None:
        files = self._state.chunk_files.setdefault(table, [])
        if path not in files:
            files.append(path)
            self.save()

    def chunk_files(self, table: str) -> list[str]:
        return list(self._state.chunk_files.get(table, []))

    def reset(self) -> None:
        """Delete checkpoint state (used before a fresh run)."""
        if self.path.exists():
            self.path.unlink()
        self._state = CheckpointState(
            config_sha256=config_sha256(self.config),
            seed=self.config.project.random_seed,
        )
        self.save()

    def save(self) -> None:
        if not self._checkpoint_enabled:
            return
        tmp = self.path.with_suffix(".tmp")
        payload = self._state.to_dict()
        try:
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            raise CheckpointError(f"Failed to write checkpoint: {exc}") from exc

    def ensure_compatible(self) -> None:
        """Raise if the on-disk checkpoint was written under different config."""
        expected = config_sha256(self.config)
        if self._state.config_sha256 and self._state.config_sha256 != expected:
            raise CheckpointError(
                "Existing checkpoint was created with a different configuration. "
                "Use --no-checkpoint or delete the checkpoint directory to restart."
            )
        if self._state.seed != self.config.project.random_seed:
            raise CheckpointError(
                "Existing checkpoint was created with a different seed. "
                "Use --no-checkpoint or delete the checkpoint directory to restart."
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_or_init(self) -> CheckpointState:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                state = CheckpointState.from_dict(data)
                _log.info(
                    "Loaded checkpoint: %d completed tables, seed=%d",
                    len(state.completed_tables),
                    state.seed,
                )
                return state
            except (OSError, json.JSONDecodeError) as exc:
                _log.warning("Ignoring corrupt checkpoint (%s); starting fresh", exc)
        return CheckpointState(
            config_sha256=config_sha256(self.config),
            seed=self.config.project.random_seed,
        )
