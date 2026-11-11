"""Relational integrity: foreign keys, orphans, duplicates.

Each declared FK is checked by anti-joining the child table against the
parent table on the FK column. Anti-join rows are violations. No fixing.
"""

from __future__ import annotations

import polars as pl

from edutrace.schemas.tables import ALL_TABLES
from edutrace.validation._report import CheckResult


def run_relational_checks(
    tables: dict[str, pl.DataFrame],
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for schema in ALL_TABLES:
        for col in schema.foreign_keys:
            parent_table, parent_col = col.foreign_key  # type: ignore[misc]
            if schema.name not in tables or parent_table not in tables:
                results.append(
                    CheckResult(
                        name=f"relational.fk.{schema.name}.{col.name}",
                        status="skip",
                        message=(
                            f"Skipped: {schema.name!r} or {parent_table!r} "
                            "not present"
                        ),
                    )
                )
                continue
            child = tables[schema.name]
            parent = tables[parent_table]
            if col.name not in child.columns or parent_col not in parent.columns:
                results.append(
                    CheckResult(
                        name=f"relational.fk.{schema.name}.{col.name}",
                        status="fail",
                        message=(
                            f"FK column {col.name!r} or parent column "
                            f"{parent_col!r} missing"
                        ),
                    )
                )
                continue

            # Filter nulls (FK optionality is a schema decision, not this
            # validator's to override).
            child_vals = child.filter(pl.col(col.name).is_not_null()).select(
                pl.col(col.name).alias("_fk")
            )
            parent_vals = parent.select(pl.col(parent_col).alias("_fk")).unique()
            orphans = child_vals.join(
                parent_vals, on="_fk", how="anti"
            ).select("_fk").unique()
            orphan_count = orphans.height
            if orphan_count > 0:
                sample = orphans["_fk"].head(10).to_list()
                results.append(
                    CheckResult(
                        name=f"relational.fk.{schema.name}.{col.name}",
                        status="fail",
                        message=(
                            f"{schema.name}.{col.name}: {orphan_count} orphaned "
                            f"value(s) not in {parent_table}.{parent_col}"
                        ),
                        details={"orphan_count": orphan_count, "sample": sample},
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name=f"relational.fk.{schema.name}.{col.name}",
                        status="pass",
                        message=(
                            f"{schema.name}.{col.name} → {parent_table}.{parent_col}: OK"
                        ),
                    )
                )
    return results
