# Troubleshooting

## `ConfigError: Configuration file not found`

You're running `python -m edutrace generate` from a directory other than the repo root, or pointing `--config` at a path that does not exist. Either `cd` to the repo root or use an absolute path.

## `ConfigError: Invalid configuration`

The YAML does not match the schema. Usually one of:

- A field name is misspelled (`num_learner` instead of `num_learners`).
- A value is out of the allowed range (`num_academic_years: 0`).
- A category is not in the enum for that field.

The error message names the specific field.

## `CheckpointError: Existing checkpoint was created with a different configuration`

You changed the config or the seed but pointed at the same checkpoint directory. Either delete `checkpoints/` or run with `--reset-checkpoint`/`--no-checkpoint`.

## `PipelineError: Table <name> not generated before write`

Indicates an orchestrator bug or a corrupted checkpoint that lists a table as complete but has no data. Delete `checkpoints/` and regenerate.

## `ValidationError: N validation check(s) failed`

The generated data violates a declared invariant. This is a code bug. Run with `--log-level DEBUG` to see the specific failing check and its `details`. Do not suppress this error in a research run.

## Out of memory during `learning_event` generation

Your `large.yaml` (or larger) is being run on insufficient RAM. Options:

- Reduce `num_learners` or `num_academic_years`.
- Ensure `pipeline.checkpoint.enabled: true` and that `_use_spill()` returns True (it does when `num_learners >= 50000` or the estimated event table exceeds ~2 GB).
- Set `output.formats: [parquet]` only.
- Run on a machine with more RAM.

## `ImportError: cannot import name 'edutrace'`

You haven't installed the package. `pip install -e .` in the repo root.

## `pytest` reports `ModuleNotFoundError: edutrace`

You're running `pytest` from outside the repo root, or the `pythonpath` config is not being picked up. `cd` to the repo root and run `python -m pytest`. The `pyproject.toml` sets `pythonpath = ["src"]` for pytest — that only works when pytest is invoked from the repo root.

## `verify` reports "Non-reproducible differences"

- You changed the config or the seed between runs (that's expected behaviour).
- Different `chunk_size` between runs — values are identical but IDs are not. Use the same chunk size.
- A library version changed between runs (NumPy, Polars). Reproducibility is guaranteed for identical versions.

## Parquet file cannot be opened by another tool

Older tools may not understand Zstandard compression. Set `output.compression: snappy` in the config.

## `duckdb` queries are slow

DuckDB reads Parquet files one at a time. For repeated analyses, create a DuckDB database (`CREATE TABLE ... AS SELECT * FROM 'file.parquet'`) and index it. See `examples/duckdb_queries.sql`.

## `CLI --help` from a script shows the top-level help

The wrapper scripts in `scripts/` call the Typer app with the subcommand prepended. Passing `--help` to those scripts shows top-level help. To see subcommand help, invoke the CLI directly:

```bash
python -m edutrace generate --help
