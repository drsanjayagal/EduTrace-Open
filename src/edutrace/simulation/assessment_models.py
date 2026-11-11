"""Assessment scoring and submission models.

These functions are pure and side-effect-free. They consume only learner
trait scalars (preparedness, engagement) and item scalars (difficulty), and
return outcome draws. All coefficients live in ``constants.SCORE_MODEL``.

The score model is a sigmoid in latent ability:

    z = intercept
        + beta_preparedness * preparedness
        + beta_engagement   * engagement
        - beta_difficulty   * item_difficulty
        - beta_prior_attempts * prior_attempts
        + N(0, noise_sd)

    score_fraction = sigmoid(z)              in (0, 1)
    score          = round(score_fraction * maximum_score, 2)

Modelling assumptions (documented, not empirical claims):

* Preparedness is the dominant ability signal.
* Engagement has a modest positive effect (opportunity to practice).
* Prior attempts reduce score (attempting more means earlier attempt was
  insufficient, so remaining attempts reflect a harder path for the same
  underlying ability).
* Noise captures unmodelled variance (cheating, illness, timing).
"""

from __future__ import annotations

import math

import numpy as np

from edutrace.constants import SCORE_MODEL


def score_attempt(
    *,
    preparedness: float,
    engagement: float,
    item_difficulty: float,
    prior_attempts: int,
    maximum_score: float,
    rng: np.random.Generator,
) -> float:
    """Return the numeric score for one attempt.

    Parameters are all scalars; ``rng`` drives the noise term. Returns a
    float in ``[0, maximum_score]`` rounded to 2 decimal places.
    """
    if maximum_score <= 0:
        raise ValueError("maximum_score must be positive")

    z = (
        SCORE_MODEL["intercept"]
        + SCORE_MODEL["beta_preparedness"] * float(preparedness)
        + SCORE_MODEL["beta_engagement"] * float(engagement)
        - SCORE_MODEL["beta_difficulty"] * float(item_difficulty)
        - SCORE_MODEL["beta_prior_attempts"] * float(prior_attempts)
        + float(rng.normal(0.0, SCORE_MODEL["noise_sd"]))
    )
    fraction = 1.0 / (1.0 + math.exp(-z))
    return round(min(maximum_score, max(0.0, fraction * maximum_score)), 2)


def sample_attempt_duration(
    assessment_type: str,
    *,
    rng: np.random.Generator,
    base_seconds: int = 900,
) -> int:
    """Draw an attempt duration in seconds.

    Exam takes longest; quizzes moderate; formative checks short. All are
    multiplicative jitter on ``base_seconds``. Modelling assumption.
    """
    multiplier = {
        "exam": 4.5,
        "assignment": 6.0,
        "project": 8.0,
        "quiz": 1.5,
        "formative_check": 0.6,
    }.get(assessment_type, 1.0)
    lam = base_seconds * multiplier
    return int(max(30, rng.gamma(2.0, lam / 2.0)))
