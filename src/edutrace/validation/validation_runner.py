"""Validation runner.

Composes every enabled validator, collects results, and optionally raises
in strict mode. Also writes a JSON report when requested.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.logging_config import get_logger
from edutrace.validation._report import ValidationReport
from edutrace.validation.consistency import run_consistency_checks
from edutrace.validation.leakage import run_leakage_checks
from edutrace.validation.relational import run_relational_checks
from edutrace.validation.reproducibility import run_reproducibility_checks
from edutrace.validation.statistical import run_statistical_checks
from edutrace.validation.structural import run_structural_checks
from edutrace.validation.temporal import run_temporal_checks

_log = get_logger(__name__)


def run_validation(
    tables: dict[str, pl.DataFrame],
    config: EduTraceConfig,
    *,
    strict: bool | None = None,
    write_report_to: str | Path | None = None,
) -> ValidationReport:
    """Run every enabled validator."""
    strict = config.validation.strict if strict is None else strict
    report = ValidationReport()

    if config.validation.check_primary_keys:
        report.extend(run_structural_checks(tables))

    if config.validation.check_foreign_keys:
        report.extend(run_relational_checks(tables))

    if config.validation.check_temporal_integrity:
        report.extend(run_temporal_checks(tables))

    report.extend(
        run_statistical_checks(
            tables, enabled=config.validation.check_distributions
        )
    )

    report.extend(run_consistency_checks(tables))

    if config.validation.check_reproducibility:
        report.extend(run_reproducibility_checks(tables, config))

    if config.validation.check_leakage:
        report.extend(run_leakage_checks(tables, config))

    if write_report_to is not None:
        report.write_json(write_report_to)

    if strict:
        report.raise_if_failed()

    return report
