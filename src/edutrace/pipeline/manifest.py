"""Dataset manifest and checksums.

After a successful run, the manifest contains:

* project metadata (name, version, seed, timezone),
* the generation profile and counts actually produced,
* row counts per table,
* SHA-256 checksums per written file,
* the schema (column names + dtypes) per table,
* the generation timestamp.

This module does *not* invent statistics. It records whatever the pipeline
actually produced (row counts, file sizes, hashes). No descriptive
statistics of the data appear here — those belong in Phase 8 analytics.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.logging_config import get_logger
from edutrace.utils.file_utils import ensure_dir
from edutrace.utils.hashing import sha256_file

_log = get_logger(__name__)


def _dtype_name(dtype: pl.DataType) -> str:
    return str(dtype)


def build_manifest(
    config: EduTraceConfig,
    tables: dict[str, pl.DataFrame],
    files: list[Path],
    *,
    root: str | Path,
) -> dict[str, Any]:
    """Return the manifest dictionary.

    Parameters
    ----------
    config:
        The pipeline configuration used for the run.
    tables:
        Mapping table-name → final DataFrame.
    files:
        All files written by the pipeline (used for checksums).
    root:
        Output root, used to compute relative paths.
    """
    root_p = Path(root)
    table_info: dict[str, Any] = {}
    for name, df in tables.items():
        table_info[name] = {
            "row_count": int(df.height),
            "column_count": int(df.width),
            "columns": [{"name": c, "dtype": _dtype_name(t)} for c, t in df.schema.items()],
        }

    file_info: list[dict[str, Any]] = []
    for f in files:
        if not Path(f).exists():
            continue
        rel = Path(f).resolve().relative_to(root_p.resolve()).as_posix()
        file_info.append(
            {
                "path": rel,
                "size_bytes": int(Path(f).stat().st_size),
                "sha256": sha256_file(f),
            }
        )

    manifest = {
        "project": {
            "name": config.project.name,
            "version": config.project.version,
            "seed": config.project.random_seed,
            "timezone": config.project.timezone,
        },
         "generation": {
            "profile": config.generation.profile,
            "num_institutions": config.generation.num_institutions,
            "num_programmes": config.generation.num_programmes,
            "num_courses_per_programme": config.generation.num_courses_per_programme,
            "num_modules_per_course": config.generation.num_modules_per_course,
            "num_learners": config.generation.num_learners,
            "num_academic_years": config.generation.num_academic_years,
            "semesters_per_year": config.generation.semesters_per_year,
            "weeks_per_semester": config.generation.weeks_per_semester,
            "resources_per_module": config.generation.resources_per_module,
            "assessment_items_per_module": config.generation.assessment_items_per_module,
            "mean_events_per_learner_week": config.generation.mean_events_per_learner_week,
            "mean_support_events_per_learner": config.generation.mean_support_events_per_learner,
        },
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "tables": table_info,
        "files": file_info,
        "caveats": [
            "All records are fully synthetic.",
            "Simulation assumptions are documented in docs/simulation_assumptions.md.",
            "No real learners, institutions, or interventions are represented.",
        ],
    }
    return manifest


def write_manifest(
    manifest: dict[str, Any],
    output_dir: str | Path,
) -> Path:
    """Write the manifest to ``<output_dir>/manifests/dataset_manifest.json``."""
    import json

    out = ensure_dir(Path(output_dir) / "manifests")
    path = out / "dataset_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _log.info("Wrote manifest → %s", path)
    return path


def write_checksums(manifest: dict[str, Any], output_dir: str | Path) -> Path:
    """Write a separate checksum file for compact diffing."""
    import json

    out = ensure_dir(Path(output_dir) / "manifests")
    path = out / "file_checksums.json"
    payload = {
        "generated_at_utc": manifest.get("generated_at_utc", ""),
        "files": [
            {"path": f["path"], "sha256": f["sha256"], "size_bytes": f["size_bytes"]}
            for f in manifest.get("files", [])
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_schema_manifest(manifest: dict[str, Any], output_dir: str | Path) -> Path:
    """Write a separate schema manifest (column names + dtypes per table)."""
    import json

    out = ensure_dir(Path(output_dir) / "manifests")
    path = out / "schema_manifest.json"
    payload = {
        "tables": {
            name: info["columns"]
            for name, info in manifest.get("tables", {}).items()
        }
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
