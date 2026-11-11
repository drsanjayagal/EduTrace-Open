"""Load a generated table with Polars and print basic statistics.

Run from repo root after generating data:
    python examples/load_parquet.py
"""

from __future__ import annotations

import polars as pl

from edutrace.analytics import descriptive, trajectories


def main() -> None:
    events_path = "data/generated/learning/learning_event.parquet"
    df = pl.read_parquet(events_path)
    print(f"learning_event: {df.height:,} rows")
    print(descriptive.table_sizes({"learning_event": df}))

    weekly_path = "data/generated/learning/weekly_engagement.parquet"
    weekly = pl.read_parquet(weekly_path)
    print("\nWeekly engagement by week:")
    print(trajectories.mean_engagement_by_week(weekly))


if __name__ == "__main__":
    main()
