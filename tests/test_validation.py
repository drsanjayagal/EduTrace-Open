from __future__ import annotations

from edutrace.validation import run_validation
from edutrace.validation.leakage import run_leakage_checks
from edutrace.validation.relational import run_relational_checks
from edutrace.validation.structural import run_structural_checks
from edutrace.validation.temporal import run_temporal_checks


def test_structural_passes_on_generated(tiny_tables):
    results = run_structural_checks(tiny_tables)
    failures = [r for r in results if r.status == "fail"]
    assert not failures, [f"{r.name}: {r.message}" for r in failures]


def test_relational_passes_on_generated(tiny_tables):
    results = run_relational_checks(tiny_tables)
    failures = [r for r in results if r.status == "fail"]
    assert not failures, [f"{r.name}: {r.message}" for r in failures]


def test_temporal_passes_on_generated(tiny_tables):
    results = run_temporal_checks(tiny_tables)
    failures = [r for r in results if r.status == "fail"]
    assert not failures, [f"{r.name}: {r.message}" for r in failures]


def test_leakage_passes_on_generated(tiny_tables, tiny_config):
    results = run_leakage_checks(tiny_tables, tiny_config)
    failures = [r for r in results if r.status == "fail"]
    assert not failures, [f"{r.name}: {r.message}" for r in failures]


def test_run_validation_full(tiny_tables, tiny_config):
    report = run_validation(tiny_tables, tiny_config, strict=False)
    errors = [r for r in report.failures if r.severity == "error"]
    assert not errors, [f"{r.name}: {r.message}" for r in errors]
