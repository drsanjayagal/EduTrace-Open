"""Academic progression, standing, and outcome models.

These are pure functions operating on scalars or small per-learner dicts.

Progression outcomes are determined at each semester-end by:

* credits attempted = sum of course credits where the learner is *active*
  or *completed* in that semester.
* credits earned = sum of course credits where the learner *completed*
  with a passing grade.
* GPA = credit-weighted mean of grade points, on a 0-10 scale:
  ``grade_point = final_grade / 10`` clipped to [0, 10]. This is a
  modelling assumption, not an empirical claim about any institution.

Outcome thresholds:
* ``earned / attempted >= 0.80`` and GPA >= 4.0  → advanced
* ``earned / attempted >= 0.55`` and GPA >= 3.5  → conditional
* ``earned / attempted >= 0.30``                 → repeated
* otherwise                                       → withdrawn

Standing thresholds (constants):
* GPA >= 5.0 → good
* GPA >= 4.0 → warning
* GPA >= 2.0 → probation
* else       → dismissed
"""

from __future__ import annotations

from edutrace.constants import (
    GRADE_POINT_DIVISOR,
    STANDING_GPA_DISMISSED,
    STANDING_GPA_PROBATION,
    STANDING_GPA_WARNING,
    AcademicStanding,
    ProgressionOutcome,
)


def grade_to_grade_point(final_grade: float | None) -> float:
    """Map a 0-100 final grade to a 0-10 grade point.

    ``None`` (no grade) maps to 0.0. Clipped to [0, 10].
    """
    if final_grade is None:
        return 0.0
    gp = float(final_grade) / GRADE_POINT_DIVISOR
    return float(min(10.0, max(0.0, gp)))


def compute_semester_gpa(
    course_credits: list[int],
    course_grades: list[float | None],
) -> float:
    """Credit-weighted mean grade point.

    Zero-credit totals produce 0.0 (documented degenerate case).
    """
    total_credits = sum(course_credits)
    if total_credits <= 0:
        return 0.0
    weighted = sum(
        credits * grade_to_grade_point(grade)
        for credits, grade in zip(course_credits, course_grades, strict=True)
    )
    return float(weighted / total_credits)


def classify_progression_outcome(
    credits_attempted: int,
    credits_earned: int,
    gpa: float,
) -> str:
    """Return a ProgressionOutcome value."""
    if credits_attempted <= 0:
        return ProgressionOutcome.WITHDRAWN.value
    ratio = credits_earned / credits_attempted
    if ratio >= 0.80 and gpa >= 4.0:
        return ProgressionOutcome.ADVANCED.value
    if ratio >= 0.55 and gpa >= 3.5:
        return ProgressionOutcome.CONDITIONAL.value
    if ratio >= 0.30:
        return ProgressionOutcome.REPEATED.value
    return ProgressionOutcome.WITHDRAWN.value


def classify_standing(gpa: float) -> str:
    """Return an AcademicStanding value."""
    if gpa >= STANDING_GPA_WARNING:
        return AcademicStanding.GOOD.value
    if gpa >= STANDING_GPA_PROBATION:
        return AcademicStanding.WARNING.value
    if gpa >= STANDING_GPA_DISMISSED:
        return AcademicStanding.PROBATION.value
    return AcademicStanding.DISMISSED.value
