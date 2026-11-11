"""Reproducibility validation.

Re-runs the deterministic structural generators with the same seed and
asserts byte-identical output. Covers ``institution``, ``programme``,
``course``, ``module``, ``learner``, and ``enrolment``. Expanded in
Phase 11 to cover learners and enrolments in addition to the original
four structural tables.

The whole check is gated by ``config.validation.check_reproducibility``
(default ``false``) so that normal pipeline runs do not pay its cost.
"""

from __future__ import annotations

from edutrace.config import EduTraceConfig
from edutrace.generators import (
    generate_courses,
    generate_enrolments,
    generate_institutions,
    generate_learners,
    generate_modules,
    generate_programmes,
)
from edutrace.utils.random_state import RandomStateManager
from edutrace.validation._report import CheckResult


def run_reproducibility_checks(
    tables: dict,
    config: EduTraceConfig,
) -> list[CheckResult]:
    results: list[CheckResult] = []

    rng_a = RandomStateManager(seed=config.project.random_seed)
    rng_b = RandomStateManager(seed=config.project.random_seed)

    inst_a = generate_institutions(config, rng_a)
    inst_b = generate_institutions(config, rng_b)
    results.append(_compare("institution", inst_a, inst_b))

    prog_a = generate_programmes(config, rng_a, inst_a)
    prog_b = generate_programmes(config, rng_b, inst_b)
    results.append(_compare("programme", prog_a, prog_b))

    courses_a = generate_courses(config, rng_a, prog_a)
    courses_b = generate_courses(config, rng_b, prog_b)
    results.append(_compare("course", courses_a, courses_b))

    mod_a = generate_modules(config, rng_a, courses_a)
    mod_b = generate_modules(config, rng_b, courses_b)
    results.append(_compare("module", mod_a, mod_b))

    learners_a = generate_learners(config, rng_a, prog_a)
    learners_b = generate_learners(config, rng_b, prog_b)
    results.append(_compare("learner", learners_a, learners_b))

    enr_a = generate_enrolments(config, rng_a, learners_a, courses_a)
    enr_b = generate_enrolments(config, rng_b, learners_b, courses_b)
    results.append(_compare("enrolment", enr_a, enr_b))

    return results


def _compare(name: str, a, b) -> CheckResult:
    check_name = f"reproducibility.{name}"
    if a.shape != b.shape:
        return CheckResult(
            name=check_name,
            status="fail",
            message=f"{name} table shape differs across runs with the same seed",
            details={"shape_a": str(a.shape), "shape_b": str(b.shape)},
        )
    if not a.equals(b):
        return CheckResult(
            name=check_name,
            status="fail",
            message=f"{name} table differs across runs with the same seed",
        )
    return CheckResult(
        name=check_name,
        status="pass",
        message=f"{name} table reproducible",
    )
