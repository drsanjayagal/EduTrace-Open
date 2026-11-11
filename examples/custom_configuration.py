"""Demonstrate overriding configuration programmatically.

Run from repo root:
    python examples/custom_configuration.py
"""

from __future__ import annotations

from pathlib import Path

from edutrace.config import apply_overrides, load_config
from edutrace.pipeline import run_pipeline


def main() -> None:
    base = load_config(Path("configs/pilot.yaml"))
    cfg = apply_overrides(
        base,
        {
            "seed": 99999,
            "num_learners": 100,
            "num_academic_years": 2,
            "output_directory": "data/generated_example_custom",
            "formats": ["parquet"],
        },
    )
    manifest = run_pipeline(cfg)
    print(f"Generated {sum(t['row_count'] for t in manifest['tables'].values()):,} rows total")


if __name__ == "__main__":
    main()
