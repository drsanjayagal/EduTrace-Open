"""Support-intervention simulation models.

At semester-end we classify each learner as *at-risk* if any of:

* mean engagement score across the semester < RISK_ENGAGEMENT_THRESHOLD
* mean attempt score < RISK_GRADE_THRESHOLD
* fraction of missed items (of course attempts possible) > MISSED_ITEM_FRACTION_THRESHOLD

At-risk learners receive zero, one, or two interventions with
probabilities drawn from a small categorical (documented). Each
intervention's type is drawn from ``INTERVENTION_TYPE_BY_TRIGGER`` given
the trigger that fired.

Response, channel, and outcome are independent categorical draws with the
declared weights. This is a modelling simplification: response is not
conditioned on the learner's prior engagement or demographics.
"""

from __future__ import annotations

import numpy as np

from edutrace.constants import (
    INTERVENTION_OUTCOME_WEIGHTS,
    INTERVENTION_TYPE_BY_TRIGGER,
    RESPONSE_STATUS_WEIGHTS,
    SUPPORT_CHANNEL_WEIGHTS,
)

# Number of interventions per at-risk learner per semester.
INTERVENTIONS_PER_AT_RISK = (0, 1, 2)
INTERVENTIONS_PER_AT_RISK_WEIGHTS = (0.25, 0.55, 0.20)


# --- Hoisted categorical arrays (Phase 7 perf optimisation). ----------------

_CHANNEL_LABELS = tuple(SUPPORT_CHANNEL_WEIGHTS.keys())
_CHANNEL_PROBS = np.array(list(SUPPORT_CHANNEL_WEIGHTS.values()), dtype=float)
_CHANNEL_PROBS = _CHANNEL_PROBS / _CHANNEL_PROBS.sum()

_RESPONSE_LABELS = tuple(RESPONSE_STATUS_WEIGHTS.keys())
_RESPONSE_PROBS = np.array(list(RESPONSE_STATUS_WEIGHTS.values()), dtype=float)
_RESPONSE_PROBS = _RESPONSE_PROBS / _RESPONSE_PROBS.sum()

_OUTCOME_LABELS = tuple(INTERVENTION_OUTCOME_WEIGHTS.keys())
_OUTCOME_PROBS = np.array(list(INTERVENTION_OUTCOME_WEIGHTS.values()), dtype=float)
_OUTCOME_PROBS = _OUTCOME_PROBS / _OUTCOME_PROBS.sum()

_COUNT_LABELS = INTERVENTIONS_PER_AT_RISK
_COUNT_PROBS = np.array(INTERVENTIONS_PER_AT_RISK_WEIGHTS, dtype=float)
_COUNT_PROBS = _COUNT_PROBS / _COUNT_PROBS.sum()


def classify_risk(
    mean_engagement: float,
    mean_attempt_score: float,
    missed_item_fraction: float,
    *,
    engagement_threshold: float,
    grade_threshold: float,
    missed_fraction_threshold: float,
) -> str | None:
    """Return the trigger label for the highest-priority risk, or None."""
    if mean_attempt_score < grade_threshold:
        return "low_score"
    if missed_item_fraction > missed_fraction_threshold:
        return "missed_assessment"
    if mean_engagement < engagement_threshold:
        return "low_engagement"
    return None


def sample_intervention_type(trigger: str, rng: np.random.Generator) -> str:
    weights = INTERVENTION_TYPE_BY_TRIGGER.get(trigger)
    if not weights:
        raise ValueError(f"Unknown intervention trigger: {trigger!r}")
    labels = tuple(weights.keys())
    probs = np.array(list(weights.values()), dtype=float)
    probs = probs / probs.sum()
    return str(rng.choice(labels, p=probs))


def sample_channel(rng: np.random.Generator) -> str:
    return str(rng.choice(_CHANNEL_LABELS, p=_CHANNEL_PROBS))


def sample_response(rng: np.random.Generator) -> str:
    return str(rng.choice(_RESPONSE_LABELS, p=_RESPONSE_PROBS))


def sample_outcome(rng: np.random.Generator) -> str:
    return str(rng.choice(_OUTCOME_LABELS, p=_OUTCOME_PROBS))


def sample_intervention_count(rng: np.random.Generator) -> int:
    return int(rng.choice(_COUNT_LABELS, p=_COUNT_PROBS))
