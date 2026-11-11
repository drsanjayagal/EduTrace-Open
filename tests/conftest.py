"""Shared fixtures for the EduTrace-Open test suite."""

from __future__ import annotations

import polars as pl
import pytest

from edutrace.config import (
    EduTraceConfig,
    GenerationConfig,
    OutputConfig,
    PipelineConfig,
    ProjectConfig,
    ValidationConfig,
)
from edutrace.pipeline import Orchestrator
from edutrace.utils.random_state import RandomStateManager


def _tiny_config() -> EduTraceConfig:
    return EduTraceConfig(
        project=ProjectConfig(random_seed=12345, timezone="UTC"),
        generation=GenerationConfig(
            profile="tiny",
            num_institutions=1,
            num_programmes=2,
            num_courses_per_programme=3,
            num_modules_per_course=2,
            num_learners=15,
            num_academic_years=2,
            semesters_per_year=2,
            weeks_per_semester=6,
            resources_per_module=2,
            assessment_items_per_module=2,
            mean_events_per_learner_week=4.0,
            mean_support_events_per_learner=0.5,
            academic_calendar_start="2024-08-01",
        ),
        output=OutputConfig(
            directory="build_test_out",
            formats=["parquet"],
            compression="snappy",
            row_group_size=10_000,
            include_manifest=True,
        ),
        # ``chunk_size`` has a strict lower bound of 1 000 in the schema.
        # Using exactly 1 000 keeps the fixture valid; the tiny learner count
        # (15) means the whole run fits in a single chunk anyway.
        pipeline=PipelineConfig(chunk_size=1_000),
        validation=ValidationConfig(
            enabled=False,
            check_reproducibility=False,
        ),
    )


@pytest.fixture(scope="session")
def tiny_config() -> EduTraceConfig:
    return _tiny_config()


@pytest.fixture(scope="session")
def tiny_tables(tiny_config, tmp_path_factory) -> dict[str, pl.DataFrame]:
    """Fully generate every table once per session, in a temp dir."""
    tmp = tmp_path_factory.mktemp("tiny_out")
    cfg = tiny_config.model_copy(deep=True)
    cfg.output.directory = str(tmp)
    cfg.pipeline.checkpoint.directory = str(tmp / "ckpt")
    cfg.pipeline.checkpoint.enabled = False
    orch = Orchestrator(config=cfg, resume=False, reset_checkpoint=True)
    orch.run()
    return orch.tables


@pytest.fixture()
def rng_manager() -> RandomStateManager:
    return RandomStateManager(seed=20261110)
