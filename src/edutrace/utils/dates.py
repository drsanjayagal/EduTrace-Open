"""Date and academic-calendar utilities.

EduTrace-Open uses a synthetic academic calendar defined by:
* ``academic_calendar_start`` (first day of semester 1 of year 1)
* ``semesters_per_year`` (usually 2)
* ``weeks_per_semester`` (usually 15)

Semesters are contiguous blocks of ``weeks_per_semester`` weeks. The break
between semesters is a fixed number of weeks (``INTERSEMESTER_GAP_WEEKS``),
which is a modelling assumption, not an empirical claim.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta

# Modelling assumption: a fixed short break between semesters.
INTERSEMESTER_GAP_WEEKS: int = 4

WEEK_DAYS: int = 7


@dataclass(frozen=True)
class AcademicCalendar:
    """Immutable academic calendar derived from config parameters."""

    start: date
    semesters_per_year: int
    weeks_per_semester: int
    num_academic_years: int

    @property
    def total_semesters(self) -> int:
        return self.semesters_per_year * self.num_academic_years

    @property
    def weeks_per_year(self) -> int:
        return self.semesters_per_year * self.weeks_per_semester

    def semester_start(self, semester_index_zero_based: int) -> date:
        """Return the Monday of week 1 of the given semester.

        ``semester_index_zero_based`` is the global semester index
        (0 .. total_semesters - 1), not the within-year index.
        """
        if semester_index_zero_based < 0:
            raise ValueError("semester index must be >= 0")
        if semester_index_zero_based >= self.total_semesters:
            raise ValueError(
                f"semester index {semester_index_zero_based} exceeds "
                f"total semesters {self.total_semesters}"
            )
        years_offset = semester_index_zero_based // self.semesters_per_year
        within_year = semester_index_zero_based % self.semesters_per_year

        block_days = (
            within_year * self.weeks_per_semester * WEEK_DAYS
            + within_year * INTERSEMESTER_GAP_WEEKS * WEEK_DAYS
            + years_offset * self.weeks_per_year * WEEK_DAYS
            + years_offset * self.semesters_per_year * INTERSEMESTER_GAP_WEEKS * WEEK_DAYS
        )
        return self.start + timedelta(days=block_days)

    def semester_end(self, semester_index_zero_based: int) -> date:
        """Return the last (Sunday) day of the given semester."""
        start = self.semester_start(semester_index_zero_based)
        return start + timedelta(days=self.weeks_per_semester * WEEK_DAYS - 1)

    def week_start(self, semester_index_zero_based: int, academic_week: int) -> date:
        """Monday of ``academic_week`` (1-based) within a semester."""
        if academic_week < 1 or academic_week > self.weeks_per_semester:
            raise ValueError(
                f"academic_week {academic_week} out of range "
                f"1..{self.weeks_per_semester}"
            )
        return self.semester_start(semester_index_zero_based) + timedelta(
            days=(academic_week - 1) * WEEK_DAYS
        )

    def iter_semesters(self) -> Iterator[int]:
        yield from range(self.total_semesters)

    def academic_year_of(self, semester_index_zero_based: int) -> int:
        return semester_index_zero_based // self.semesters_per_year + 1

    def semester_within_year(self, semester_index_zero_based: int) -> int:
        return semester_index_zero_based % self.semesters_per_year + 1


def random_timestamp_within(
    start: date,
    end: date,
    weight_hours: tuple[float, ...] | None = None,
    *,
    rng=None,
) -> datetime:
    """Return a random datetime in ``[start, end)`` with an hour-of-day bias.

    ``weight_hours`` optionally supplies a 24-length tuple of relative weights
    per hour of day. When ``None``, a plausible study-hours profile is used.
    This is a documented modelling assumption, not an empirical claim.
    """
    import numpy as np

    if end <= start:
        raise ValueError("end must be strictly after start")
    if rng is None:
        rng = np.random.default_rng()

    if weight_hours is None:
        # Study-hours bias: quiet overnight, peaks in evening.
        weight_hours = (
            0.2, 0.1, 0.1, 0.1, 0.1, 0.2,
            0.5, 1.0, 1.5, 2.0, 2.0, 1.8,
            1.4, 1.2, 1.4, 1.8, 2.2, 2.6,
            3.0, 2.8, 2.2, 1.5, 0.8, 0.4,
        )
    weights = np.asarray(weight_hours, dtype=float)
    if weights.shape != (24,):
        raise ValueError("weight_hours must have exactly 24 entries")

    total_days = (end - start).days
    day_offset = int(rng.integers(0, max(total_days, 1)))
    hour = int(rng.choice(24, p=weights / weights.sum()))
    minute = int(rng.integers(0, 60))
    second = int(rng.integers(0, 60))

    return datetime.combine(start, datetime.min.time()) + timedelta(
        days=day_offset, hours=hour, minutes=minute, seconds=second
    )


def ensure_utc_naive(dt: datetime) -> datetime:
    """Return a timezone-naive datetime.

    The dataset stores naive datetimes in the configured timezone. If a
    tz-aware datetime is passed, it is converted to UTC and stripped.
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt
