"""Configuration loading and validation for EduTrace-Open.

The configuration model is defined with Pydantic so that bad YAML is caught
before any generation begins. CLI overrides are applied via
:func:`apply_overrides`, which mutates a copy of the loaded model and
re-validates it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from edutrace.constants import DEFAULT_RANDOM_SEED
from edutrace.exceptions import ConfigError

OutputFormat = Literal["parquet", "csv", "jsonl"]


class ProjectConfig(BaseModel):
    name: str = "EduTrace-Open"
    version: str = "0.1.0"
    random_seed: int = DEFAULT_RANDOM_SEED
    timezone: str = "Asia/Kolkata"

    @field_validator("random_seed")
    @classmethod
    def _seed_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("random_seed must be >= 0")
        return v


class GenerationConfig(BaseModel):
    profile: str = "default"
    num_institutions: int = Field(1, ge=1)
    num_programmes: int = Field(5, ge=1)
    num_courses_per_programme: int = Field(6, ge=1)
    num_modules_per_course: int = Field(4, ge=1)
    num_learners: int = Field(1000, ge=1)
    num_academic_years: int = Field(3, ge=1, le=10)
    semesters_per_year: int = Field(2, ge=1, le=3)
    weeks_per_semester: int = Field(15, ge=1, le=30)
    resources_per_module: int = Field(6, ge=1)
    assessment_items_per_module: int = Field(3, ge=1)
    mean_events_per_learner_week: float = Field(12.0, ge=0.0)
    mean_support_events_per_learner: float = Field(0.6, ge=0.0)
    academic_calendar_start: str = "2023-08-01"

    @model_validator(mode="after")
    def _validate_counts(self) -> GenerationConfig:
        if self.num_programmes > 100 * self.num_institutions:
            raise ValueError(
                "num_programmes exceeds 100x num_institutions; "
                "check that this is intentional."
            )
        return self


class OutputConfig(BaseModel):
    directory: str = "data/generated"
    formats: list[OutputFormat] = Field(default_factory=lambda: ["parquet", "csv"])
    compression: str = "zstd"
    row_group_size: int = Field(200_000, ge=1_000)
    include_manifest: bool = True


class CheckpointConfig(BaseModel):
    enabled: bool = True
    directory: str = "checkpoints"
    every_n_learners: int = Field(10_000, ge=100)


class PipelineConfig(BaseModel):
    chunk_size: int = Field(50_000, ge=1_000)
    checkpoint: CheckpointConfig = Field(default_factory=CheckpointConfig)


class ValidationConfig(BaseModel):
    enabled: bool = True
    strict: bool = False
    check_primary_keys: bool = True
    check_foreign_keys: bool = True
    check_temporal_integrity: bool = True
    check_distributions: bool = True
    check_leakage: bool = True
    check_reproducibility: bool = False  # expensive; opt-in


class EduTraceConfig(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)


def load_config(path: str | Path) -> EduTraceConfig:
    """Load and validate a YAML configuration file.

    Raises :class:`ConfigError` on missing files, malformed YAML, or schema
    violations.
    """
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"Configuration file not found: {p}")

    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Malformed YAML in {p}: {exc}") from exc

    if raw is None:
        raise ConfigError(f"Configuration file {p} is empty")
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Configuration file {p} must contain a mapping at the top level"
        )

    try:
        return EduTraceConfig.model_validate(raw)
    except Exception as exc:  # pydantic ValidationError subclass
        raise ConfigError(f"Invalid configuration in {p}: {exc}") from exc


# Mapping of CLI-overridable dotted paths to (section, field).
_OVERRIDES: dict[str, tuple[str, str]] = {
    "seed": ("project", "random_seed"),
    "output_directory": ("output", "directory"),
    "num_learners": ("generation", "num_learners"),
    "num_academic_years": ("generation", "num_academic_years"),
    "chunk_size": ("pipeline", "chunk_size"),
}


def apply_overrides(config: EduTraceConfig, overrides: dict[str, Any]) -> EduTraceConfig:
    """Return a copy of ``config`` with CLI overrides applied.

    Unknown override keys raise :class:`ConfigError`. ``None`` values are
    ignored so that callers can pass ``argparse``-style namespaces safely.
    """
    data = config.model_dump()

    for key, value in overrides.items():
        if value is None:
            continue
        if key == "formats":
            data["output"]["formats"] = list(value)
            continue
        if key == "log_level":
            # handled by CLI, not stored on config
            continue
        if key not in _OVERRIDES:
            raise ConfigError(f"Unknown override: {key}")
        section, field = _OVERRIDES[key]
        data[section][field] = value

    try:
        return EduTraceConfig.model_validate(data)
    except Exception as exc:
        raise ConfigError(f"Invalid overridden configuration: {exc}") from exc


def dump_config(config: EduTraceConfig) -> dict[str, Any]:
    """Return a JSON-safe dictionary representation of the configuration."""
    return config.model_dump(mode="json")
