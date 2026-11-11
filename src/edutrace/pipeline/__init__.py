"""Data pipeline: dependency management, chunked generation, checkpointing,
manifest/checksum generation, and export utilities."""

from __future__ import annotations

from edutrace.pipeline.checkpoint import CheckpointManager
from edutrace.pipeline.chunk_writer import ChunkWriter
from edutrace.pipeline.dependency_manager import (
    TABLE_DEPENDENCIES,
    ensure_valid_order,
    topological_order,
)
from edutrace.pipeline.export_manager import export_formats
from edutrace.pipeline.manifest import build_manifest, write_manifest
from edutrace.pipeline.orchestrator import Orchestrator, run_pipeline

__all__ = [
    "TABLE_DEPENDENCIES",
    "ensure_valid_order",
    "topological_order",
    "CheckpointManager",
    "ChunkWriter",
    "export_formats",
    "build_manifest",
    "write_manifest",
    "Orchestrator",
    "run_pipeline",
]
