"""Rough memory-estimation utilities.

These estimates are approximations used to warn operators before they launch
a run that would exhaust RAM. They are not promises; actual memory usage
depends on dtypes, Arrow metadata, and OS caching.
"""

from __future__ import annotations


def estimate_learning_event_bytes(
    num_learners: int,
    mean_events_per_learner_week: float,
    weeks_per_semester: int,
    semesters: int,
    *,
    bytes_per_row: int = 260,
) -> int:
    """Rough peak-memory estimate for the learning_event table.

    ``bytes_per_row`` is an approximate in-memory cost of one event record
    held in a Pandas/Polars frame. This is deliberately conservative.
    """
    total_events = int(
        num_learners
        * mean_events_per_learner_week
        * weeks_per_semester
        * semesters
    )
    return total_events * bytes_per_row


def format_bytes(n: int) -> str:
    """Human-readable byte count (base-1024)."""
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or unit == "TiB":
            return f"{n:.1f} {unit}"
        n = n / 1024  # type: ignore[assignment]
    return f"{n:.1f} TiB"
