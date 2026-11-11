"""Temporal helpers for event timing.

Kept separate from ``utils/dates.py`` because these carry *simulation*
policy (which hour-of-day profile to use, how to sample a timestamp inside
a week), not just calendar arithmetic.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np

# Per-channel hour-of-day weight profiles (24 entries each). Modelling
# assumption, not empirical claim.
_WEB_HOURS = (
    0.2, 0.1, 0.1, 0.1, 0.1, 0.2,
    0.5, 1.0, 1.5, 2.0, 2.0, 1.8,
    1.4, 1.2, 1.4, 1.8, 2.2, 2.6,
    3.0, 2.8, 2.2, 1.5, 0.8, 0.4,
)
_MOBILE_HOURS = (
    0.3, 0.2, 0.2, 0.1, 0.1, 0.2,
    0.6, 1.2, 1.6, 1.8, 1.8, 1.6,
    1.4, 1.3, 1.5, 1.8, 2.0, 2.4,
    2.8, 3.0, 2.6, 1.8, 1.0, 0.5,
)
_DESKTOP_HOURS = (
    0.0, 0.0, 0.0, 0.0, 0.0, 0.1,
    0.3, 0.8, 1.5, 2.2, 2.5, 2.2,
    1.6, 1.5, 1.8, 2.2, 2.4, 2.6,
    2.6, 2.0, 1.2, 0.6, 0.2, 0.1,
)

_CHANNEL_PROFILES: dict[str, tuple[float, ...]] = {
    "web": _WEB_HOURS,
    "mobile": _MOBILE_HOURS,
    "tablet": _MOBILE_HOURS,
    "desktop_app": _DESKTOP_HOURS,
    "api": _WEB_HOURS,
}

INTERACTION_CHANNEL_WEIGHTS = {
    "web": 0.40,
    "mobile": 0.35,
    "tablet": 0.10,
    "desktop_app": 0.13,
    "api": 0.02,
}


def sample_channel(rng: np.random.Generator) -> str:
    """Draw an interaction channel from the weighted profile."""
    labels = tuple(INTERACTION_CHANNEL_WEIGHTS.keys())
    probs = np.array(list(INTERACTION_CHANNEL_WEIGHTS.values()), dtype=float)
    probs = probs / probs.sum()
    return str(rng.choice(labels, p=probs))


def sample_timestamp_in_week(
    week_start: date,
    channel: str,
    rng: np.random.Generator,
) -> datetime:
    """Return a timestamp within ``[week_start, week_start + 7d)``.

    Uses the channel-specific hour-of-day profile. Modelling assumption.
    """
    profile = _CHANNEL_PROFILES.get(channel, _WEB_HOURS)
    weights = np.asarray(profile, dtype=float)
    weights = weights / weights.sum()

    day_offset = int(rng.integers(0, 7))
    hour = int(rng.choice(24, p=weights))
    minute = int(rng.integers(0, 60))
    second = int(rng.integers(0, 60))
    return datetime.combine(week_start, datetime.min.time()) + timedelta(
        days=day_offset, hours=hour, minutes=minute, seconds=second
    )


def sample_duration_seconds(
    event_type: str,
    rng: np.random.Generator,
    *,
    video_range: tuple[int, int] = (180, 1800),
    reading_range: tuple[int, int] = (120, 900),
    quiz_range: tuple[int, int] = (300, 1800),
    other_range: tuple[int, int] = (30, 600),
) -> int:
    """Draw a duration in seconds appropriate for ``event_type``."""
    if event_type in ("video_start", "video_pause", "video_complete"):
        lo, hi = video_range
    elif event_type in ("resource_view", "resource_download"):
        lo, hi = reading_range
    elif event_type in ("quiz_open", "quiz_submit"):
        lo, hi = quiz_range
    else:
        lo, hi = other_range
    return int(rng.integers(lo, hi + 1))
