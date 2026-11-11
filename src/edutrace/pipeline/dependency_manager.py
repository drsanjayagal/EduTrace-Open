"""Table dependency graph and topological ordering.

The graph is a static declaration of which tables must be generated before
which other tables. The orchestrator (``orchestrator.py``) uses it to walk
tables in a valid order and to expose clear errors when a caller requests
an invalid order.
"""

from __future__ import annotations

from edutrace.schemas.tables import ALL_TABLES

# Each table maps to the set of tables it directly depends on.
# Note: `enrolment` depends on both `learner` and `course`. `learning_event`
# depends on `enrolment`, `module`, and `learning_resource` (module and
# resource tables must be complete before events are generated).
TABLE_DEPENDENCIES: dict[str, frozenset[str]] = {
    "institution": frozenset(),
    "programme": frozenset({"institution"}),
    "course": frozenset({"programme"}),
    "module": frozenset({"course"}),
    "curriculum_dependency": frozenset({"module", "course"}),
    "learner": frozenset({"programme"}),
    "enrolment": frozenset({"learner", "course"}),
    "learning_resource": frozenset({"module", "course"}),
    "learning_event": frozenset({"enrolment", "module", "learning_resource"}),
    "assessment_item": frozenset({"module", "course"}),
    "assessment_attempt": frozenset({"enrolment", "assessment_item"}),
    "feedback_event": frozenset({"assessment_attempt"}),
    "weekly_engagement": frozenset({"learning_event", "enrolment"}),
    "progression_event": frozenset({"learner", "enrolment", "course", "programme"}),
    "digital_access": frozenset({"learner"}),
    "support_event": frozenset(
        {"learner", "enrolment", "weekly_engagement", "assessment_attempt"}
    ),
}


def _declared_tables() -> frozenset[str]:
    return frozenset(TABLE_DEPENDENCIES.keys())


def ensure_valid_order(order: list[str]) -> None:
    """Raise ``ValueError`` if ``order`` violates the dependency graph.

    Checks:
    * every table in ``order`` is declared;
    * every dependency of a table appears earlier in ``order``;
    * every declared table appears exactly once.
    """
    declared = _declared_tables()
    schema_tables = {t.name for t in ALL_TABLES}
    if declared != schema_tables:
        raise ValueError(
            "Dependency graph and schema tables disagree: "
            f"missing={sorted(schema_tables - declared)}, "
            f"extra={sorted(declared - schema_tables)}"
        )
    if len(set(order)) != len(order):
        raise ValueError("Order contains duplicate tables")
    if set(order) != declared:
        raise ValueError(
            f"Order must contain exactly the declared tables; "
            f"missing={sorted(declared - set(order))}, "
            f"extra={sorted(set(order) - declared)}"
        )

    seen: set[str] = set()
    for table in order:
        for dep in TABLE_DEPENDENCIES[table]:
            if dep not in seen:
                raise ValueError(
                    f"Table {table!r} depends on {dep!r} but {dep!r} does not "
                    f"precede it in the requested order"
                )
        seen.add(table)


def topological_order() -> list[str]:
    """Return a valid deterministic topological order.

    Ties broken by the declared schema order (ALL_TABLES), so the result is
    stable across Python versions.
    """
    schema_order = [t.name for t in ALL_TABLES]
    remaining = set(schema_order)
    resolved: list[str] = []
    while remaining:
        ready = [
            t for t in schema_order
            if t in remaining and TABLE_DEPENDENCIES[t].issubset(set(resolved))
        ]
        if not ready:
            raise ValueError(
                f"No table is ready; remaining={sorted(remaining)}"
            )
        # Pick the first ready table in schema order, for determinism.
        next_table = ready[0]
        resolved.append(next_table)
        remaining.discard(next_table)
    return resolved
