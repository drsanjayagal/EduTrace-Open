"""Stable identifier formatting and row-key derivation for EduTrace-Open.

Every table has a documented prefix. IDs are constructed as
``prefix_<zero-padded-int>`` so they are sortable, human-readable, and stable
across chunk sizes.

``row_key_from_ints`` is the deterministic hashing helper used by every
generator that needs a per-row RNG seed. Its job is to combine up to four
small integer parts into a single integer that is (a) collision-free across
the range of inputs actually used, and (b) stable across runs and platforms.
"""

from __future__ import annotations

import numpy as np

ID_WIDTH: int = 8

PREFIX_INSTITUTION = "inst"
PREFIX_PROGRAMME = "prog"
PREFIX_COURSE = "crs"
PREFIX_MODULE = "mod"
PREFIX_LEARNER = "lrn"
PREFIX_ENROLMENT = "enr"
PREFIX_RESOURCE = "res"
PREFIX_EVENT = "evt"
PREFIX_ASSESSMENT_ITEM = "asit"
PREFIX_ATTEMPT = "att"
PREFIX_FEEDBACK = "fbk"
PREFIX_WEEKLY = "wk"
PREFIX_PROGRESSION = "prg"
PREFIX_ACCESS = "acc"
PREFIX_SUPPORT = "sup"
PREFIX_DEPENDENCY = "dep"


def format_id(prefix: str, n: int) -> str:
    """Return a zero-padded identifier like ``lrn_00000042``."""
    if n < 0:
        raise ValueError(f"Identifier number must be >= 0, got {n}")
    return f"{prefix}_{n:0{ID_WIDTH}d}"


def format_ids(prefix: str, values: np.ndarray) -> np.ndarray:
    """Vectorised :func:`format_id` over a NumPy integer array."""
    values = np.asarray(values)
    if values.ndim != 1:
        raise ValueError("format_ids expects a 1-D integer array")
    if not np.issubdtype(values.dtype, np.integer):
        raise ValueError(f"format_ids expects integer dtype, got {values.dtype}")
    if values.size and values.min() < 0:
        raise ValueError("format_ids received negative identifier numbers")
    return np.array(
        [f"{prefix}_{v:0{ID_WIDTH}d}" for v in values.tolist()], dtype=object
    )


def parse_id(value: str) -> tuple[str, int]:
    """Split an identifier into ``(prefix, numeric_part)``."""
    if not isinstance(value, str) or "_" not in value:
        raise ValueError(f"Not a valid identifier: {value!r}")
    prefix, _, suffix = value.rpartition("_")
    if not prefix or not suffix.isdigit():
        raise ValueError(f"Not a valid identifier: {value!r}")
    return prefix, int(suffix)


# Positional encoding bounds for row_key_from_ints.
#   part[0]: learner or entity number
#   part[1]: semester / enrolment / item / arbitrary index
#   part[2]: arbitrary index
#   part[3]: attempt / sequence number
#
# Each bound is 100_000_000 (10^8), which comfortably accommodates:
#   - up to 100 million learners
#   - up to 100 million enrolments (large.yaml produces ~650k)
#   - up to 100 million items per module
#   - up to 100 million attempts per item
#
# This was widened after the standard profile (10 000 learners) hit
# ``Part 10000 exceeds bound 10000`` — ``enrolment_num`` grows much faster
# than ``learner_num`` because each learner has multiple enrolments, so a
# slot sized to the number of learners was not large enough for the
# enrolment index. The slack is free: keys are Python ints and their size
# has no bearing on RNG cost.
_ROW_KEY_BOUNDS: tuple[int, ...] = (
    100_000_000,
    100_000_000,
    100_000_000,
    100_000_000,
)


def row_key_from_ints(*parts: int) -> int:
    """Combine several small non-negative ints into a stable row key.

    Positional encoding with fixed per-position bounds declared in
    ``_ROW_KEY_BOUNDS``. Raises ``ValueError`` on negative input or on a
    part exceeding its bound, so silent collisions cannot happen.
    """
    if not parts:
        raise ValueError("row_key_from_ints requires at least one part")
    if len(parts) > len(_ROW_KEY_BOUNDS):
        raise ValueError(
            f"At most {len(_ROW_KEY_BOUNDS)} parts are supported"
        )
    key = 0
    for part, bound in zip(parts, _ROW_KEY_BOUNDS, strict=False):
        if part < 0:
            raise ValueError(f"Negative part in row_key_from_ints: {part}")
        if part >= bound:
            raise ValueError(
                f"Part {part} exceeds bound {bound} in row_key_from_ints"
            )
        key = key * bound + part
    return key
