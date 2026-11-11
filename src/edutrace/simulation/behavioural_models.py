"""Behavioural simulation models.

These are pure functions that return per-learner parameters consumed by the
event and assessment generators. They contain no I/O and no global state.

The parameters are *modelling assumptions* — documented in the docstrings
and in ``docs/simulation_assumptions.md`` (Phase 11). They are not claimed
to reflect any real population.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from edutrace.constants import WEEKLY_ENGAGEMENT_MULTIPLIERS


@dataclass(frozen=True)
class LearnerBehaviour:
    """Behavioural parameters for one learner."""

    learner_key: int
    base_event_rate: float
    engagement_state: float
    preference_bias: dict[str, float]


def build_learner_behaviours(
    learner_keys: list[int],
    prepared: list[float],
    engagement: list[float],
    preference: list[str],
    mean_events_per_learner_week: float,
) -> list[LearnerBehaviour]:
    """Return one :class:`LearnerBehaviour` per learner."""
    if not (len(learner_keys) == len(prepared) == len(engagement) == len(preference)):
        raise ValueError("Learner parameter lists must be the same length")

    out: list[LearnerBehaviour] = []
    for key, _prep, eng, pref in zip(
        learner_keys, prepared, engagement, preference, strict=True
    ):
        rate = float(mean_events_per_learner_week * (0.6 + 0.8 * float(eng)))
        if rate <= 0.0:
            rate = 0.5
        out.append(
            LearnerBehaviour(
                learner_key=key,
                base_event_rate=rate,
                engagement_state=float(eng),
                preference_bias=_preference_bias(pref),
            )
        )
    return out


def _preference_bias(pref: str) -> dict[str, float]:
    """Multiplicative bias per resource type, given a preference label."""
    bias = {
        "lecture_video": 1.0,
        "reading": 1.0,
        "slide_deck": 1.0,
        "quiz": 1.0,
        "assignment_brief": 1.0,
        "discussion_thread": 1.0,
    }
    if pref == "video_first":
        bias["lecture_video"] = 1.4
        bias["reading"] = 0.85
    elif pref == "reading_first":
        bias["lecture_video"] = 0.85
        bias["reading"] = 1.4
    elif pref == "interactive_first":
        bias["quiz"] = 1.4
        bias["discussion_thread"] = 1.3
        bias["lecture_video"] = 0.9
    elif pref == "discussion_first":
        bias["discussion_thread"] = 1.6
        bias["reading"] = 1.1
    return bias


def week_phase(academic_week: int, weeks_per_semester: int) -> str:
    """Classify a week into a phase label.

    early: weeks 1-2
    late: last week
    mid: everything else
    """
    if academic_week <= 2:
        return "early"
    if academic_week >= weeks_per_semester:
        return "late"
    return "mid"


def weekly_multiplier(academic_week: int, weeks_per_semester: int) -> float:
    """Return the weekly engagement multiplier for a given week."""
    phase = week_phase(academic_week, weeks_per_semester)
    if phase == "early":
        return (
            WEEKLY_ENGAGEMENT_MULTIPLIERS["very_early"]
            if academic_week == 1
            else WEEKLY_ENGAGEMENT_MULTIPLIERS["early"]
        )
    if phase == "late":
        return (
            WEEKLY_ENGAGEMENT_MULTIPLIERS["final"]
            if academic_week == weeks_per_semester
            else WEEKLY_ENGAGEMENT_MULTIPLIERS["late"]
        )
    return WEEKLY_ENGAGEMENT_MULTIPLIERS["mid"]


def sample_weekly_event_count(
    behaviour: LearnerBehaviour,
    academic_week: int,
    weeks_per_semester: int,
    rng: np.random.Generator,
) -> int:
    """Draw the Poisson event count for one learner-week."""
    multiplier = weekly_multiplier(academic_week, weeks_per_semester)
    lam = behaviour.base_event_rate * multiplier
    if lam <= 0.0:
        return 0
    return int(rng.poisson(lam))


def next_engagement_state(
    current: float,
    rng: np.random.Generator,
    *,
    reversion: float = 0.15,
    noise_sd: float = 0.05,
    target: float = 0.6,
) -> float:
    """Mean-reverting random walk for engagement state."""
    delta = reversion * (target - current) + rng.normal(0.0, noise_sd)
    new = float(np.clip(current + delta, 0.02, 0.99))
    return new


def weekly_engagement_scalar(
    event_count: int,
    mean_events_per_learner_week: float,
) -> float:
    """Map raw event count to a [0, 1] engagement scalar."""
    if mean_events_per_learner_week <= 0.0:
        return 0.0
    return float(min(1.0, event_count / (2.0 * mean_events_per_learner_week)))


def classify_trajectory(engagement_scalar: float) -> str:
    """Map a scalar engagement score to a TrajectoryState label.

    Thresholds are modelling assumptions:
      thriving    >= 0.70
      steady      0.40 - 0.70
      at_risk     0.15 - 0.40
      disengaged  < 0.15
    """
    if engagement_scalar >= 0.70:
        return "thriving"
    if engagement_scalar >= 0.40:
        return "steady"
    if engagement_scalar >= 0.15:
        return "at_risk"
    return "disengaged"
