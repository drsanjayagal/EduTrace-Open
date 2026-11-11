"""Validation subsystem for EduTrace-Open.

Public API:
* :func:`run_validation` — run every enabled validator.
* :class:`ValidationReport`, :class:`CheckResult` — result types.
* Individual modules are importable for advanced use.
"""

from __future__ import annotations

from edutrace.validation._report import CheckResult, ValidationReport
from edutrace.validation.validation_runner import run_validation

__all__ = [
    "CheckResult",
    "ValidationReport",
    "run_validation",
]
