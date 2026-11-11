"""Deterministic random-number management for EduTrace-Open.

Design
------
We derive every RNG from a single master seed through
``numpy.random.SeedSequence``:

    master = SeedSequence(seed)
    table_ss = master.spawn_key(table_name)  # actually: derived

Concretely:
    master = SeedSequence(seed)
    table_ss = SeedSequence(entropy=seed, spawn_key=(table_index,))
    per_row_rng = np.random.default_rng(SeedSequence(entropy=seed, spawn_key=(table_index, row_key)))

The row-level spawning means the values produced for a given logical entity
(e.g. ``learner_00000042``) never depend on how many other rows are generated
first, on chunk size, or on generation order. This is the strict
"chunk-size-independent reproducibility" guarantee referred to in the design
notes.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

# Registry of table names to small, stable integer indices. Never reorder —
# doing so would change the derived RNG stream for a given seed.
_TABLE_INDEX: dict[str, int] = {
    "institution": 1,
    "programme": 2,
    "course": 3,
    "module": 4,
    "curriculum_dependency": 5,
    "learner": 6,
    "enrolment": 7,
    "learning_resource": 8,
    "learning_event": 9,
    "assessment_item": 10,
    "assessment_attempt": 11,
    "feedback_event": 12,
    "weekly_engagement": 13,
    "progression_event": 14,
    "digital_access": 15,
    "support_event": 16,
}


def table_index(name: str) -> int:
    """Return the stable integer index for a table name."""
    try:
        return _TABLE_INDEX[name]
    except KeyError as exc:
        raise ValueError(f"Unknown table name: {name!r}") from exc


@dataclass(frozen=True)
class RandomStateManager:
    """Root RNG manager bound to a seed.

    This object is immutable; deriving child generators does not mutate it.
    """

    seed: int

    def _table_seed(self, table: str) -> np.random.SeedSequence:
        return np.random.SeedSequence(
            entropy=self.seed, spawn_key=(table_index(table),)
        )

    def table_rng(self, table: str) -> np.random.Generator:
        """RNG scoped to a whole table.

        Use this for structural choices (e.g. sampling module difficulty
        levels) where row-level independence is not required.
        """
        return np.random.default_rng(self._table_seed(table))

    def row_rng(self, table: str, row_key: int | str) -> np.random.Generator:
        """RNG scoped to a single logical row.

        ``row_key`` is typically the integer primary-key number
        (e.g. ``42`` for ``lrn_00000042``). Use this for any value that
        belongs to a specific row so reproducibility never depends on chunk
        boundaries or generation order.
        """
        if isinstance(row_key, str):
            # Convert arbitrary strings to a stable integer via a bounded hash.
            from edutrace.utils.hashing import stable_int_hash

            row_key = stable_int_hash(row_key)
        return np.random.default_rng(
            np.random.SeedSequence(
                entropy=self.seed,
                spawn_key=(table_index(table), int(row_key)),
            )
        )

    def spawn(self, label: str) -> RandomStateManager:
        """Create a derived manager for a sub-simulation.

        Useful when an analytical module (e.g. leakage detection) needs its
        own seed without disturbing the main stream.
        """
        from edutrace.utils.hashing import stable_int_hash

        child_seed = (self.seed ^ stable_int_hash(label)) & 0xFFFF_FFFF
        return RandomStateManager(seed=child_seed)


def derive_rngs(manager: RandomStateManager, tables: Iterable[str]) -> dict[str, np.random.Generator]:
    """Convenience helper: one table-scoped RNG per name."""
    return {t: manager.table_rng(t) for t in tables}
