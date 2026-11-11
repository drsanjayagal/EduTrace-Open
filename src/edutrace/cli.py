"""Command-line interface for EduTrace-Open.

Commands
--------
* ``generate``  — build a dataset from a YAML config.
* ``validate``  — run validators against an existing dataset on disk.
* ``inspect``   — print descriptive summaries.
* ``export``    — convert an existing dataset to additional formats.
* ``verify``    — end-to-end reproducibility check under a temp dir.

The CLI delegates to library functions; it does not reimplement logic.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console
from rich.table import Table

from edutrace import __version__
from edutrace.config import EduTraceConfig, apply_overrides, load_config
from edutrace.exceptions import (
    ConfigError,
    EduTraceError,
    PipelineError,
    ValidationError,
)
from edutrace.logging_config import configure_logging, get_logger
from edutrace.pipeline.orchestrator import Orchestrator

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="EduTrace-Open — synthetic higher-education dataset generator.",
)
console = Console()
_log = get_logger("cli")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _fail(msg: str, code: int = 1) -> NoReturn:
    console.print(f"[red]{msg}[/red]")
    raise typer.Exit(code=code)


def _load_config_or_die(
    config_path: Path,
    *,
    seed: int | None,
    output: Path | None,
    learners: int | None,
    years: int | None,
    chunk_size: int | None,
    formats: list[str] | None,
) -> EduTraceConfig:
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        _fail(f"Config error: {exc}", code=2)

    overrides: dict = {
        "seed": seed,
        "output_directory": str(output) if output else None,
        "num_learners": learners,
        "num_academic_years": years,
        "chunk_size": chunk_size,
    }
    if formats:
        overrides["formats"] = formats
    try:
        return apply_overrides(cfg, overrides)
    except ConfigError as exc:
        _fail(f"Override error: {exc}", code=2)


def _print_summary(manifest: dict) -> None:
    table = Table(title="Generated tables")
    table.add_column("Table")
    table.add_column("Rows", justify="right")
    for name, info in sorted(manifest.get("tables", {}).items()):
        table.add_row(name, f"{info['row_count']:,}")
    console.print(table)
    console.print(
        f"[green]Manifest written under "
        f"{manifest.get('project', {}).get('name', 'EduTrace-Open')} output dir[/green]"
    )


def _table_hashes(tables: dict) -> dict[str, str]:
    from edutrace.utils.hashing import stable_frame_hash

    return {name: stable_frame_hash(df, sample=50_000) for name, df in tables.items()}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def generate(
    config: Path = typer.Option(
        Path("configs/pilot.yaml"),
        "--config",
        "-c",
        help="Path to YAML configuration.",
    ),
    seed: int | None = typer.Option(None, "--seed", help="Override random seed."),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Override output directory."
    ),
    learners: int | None = typer.Option(
        None, "--learners", help="Override num_learners."
    ),
    years: int | None = typer.Option(
        None, "--years", help="Override num_academic_years."
    ),
    chunk_size: int | None = typer.Option(
        None, "--chunk-size", help="Override pipeline.chunk_size."
    ),
    formats: list[str] | None = typer.Option(
        None, "--format", "-f", help="Output format (repeatable)."
    ),
    log_level: str = typer.Option("INFO", "--log-level"),
    no_checkpoint: bool = typer.Option(
        False,
        "--no-checkpoint",
        help="Ignore existing checkpoints and start fresh.",
    ),
    reset_checkpoint: bool = typer.Option(
        False,
        "--reset-checkpoint",
        help="Delete checkpoint state before running.",
    ),
) -> None:
    """Generate the dataset described by a config."""
    configure_logging(log_level)
    cfg = _load_config_or_die(
        config,
        seed=seed,
        output=output,
        learners=learners,
        years=years,
        chunk_size=chunk_size,
        formats=formats,
    )
    try:
        orchestrator = Orchestrator(
            config=cfg,
            resume=not no_checkpoint,
            reset_checkpoint=reset_checkpoint,
        )
        manifest = orchestrator.run()
    except ValidationError as exc:
        _fail(f"Validation failed: {exc}", code=1)
    except (PipelineError, EduTraceError) as exc:
        _fail(f"Pipeline error: {exc}", code=1)
    except Exception as exc:
        _log.exception("Unexpected error")
        _fail(f"Unexpected error: {exc}", code=3)

    _print_summary(manifest)
    console.print(f"[green]Done.[/green] Output: {cfg.output.directory}")


@app.command()
def validate(
    input: Path = typer.Option(
        ..., "--input", "-i", help="Directory containing generated tables."
    ),
    config: Path = typer.Option(
        Path("configs/pilot.yaml"),
        "--config",
        "-c",
        help="Config used for enabling/disabling checks.",
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Exit non-zero on any failure."
    ),
    report: Path | None = typer.Option(
        None, "--report", help="Write JSON report to this path."
    ),
    log_level: str = typer.Option("INFO", "--log-level"),
) -> None:
    """Validate a dataset that already exists on disk."""
    configure_logging(log_level)
    from edutrace.analytics import load_dataset_from_disk
    from edutrace.validation import run_validation

    cfg = _load_config_or_die(
        config,
        seed=None,
        output=None,
        learners=None,
        years=None,
        chunk_size=None,
        formats=None,
    )
    try:
        tables = load_dataset_from_disk(input)
    except FileNotFoundError as exc:
        _fail(str(exc), code=2)

    report_obj = run_validation(tables, cfg, strict=False)

    table = Table(title="Validation results")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")
    for r in report_obj.results:
        colour = {"pass": "green", "fail": "red", "skip": "yellow"}[r.status]
        table.add_row(r.name, f"[{colour}]{r.status}[/{colour}]", r.message)
    console.print(table)

    if report:
        p = report_obj.write_json(report)
        console.print(f"[green]JSON report → {p}[/green]")

    if strict and not report_obj.ok:
        raise typer.Exit(code=1)


@app.command()
def inspect(
    input: Path = typer.Option(
        ..., "--input", "-i", help="Directory containing generated tables."
    ),
    max_categorical: int = typer.Option(
        6, "--top", help="Top-N per categorical."
    ),
    json_out: Path | None = typer.Option(
        None, "--json", help="Write the full summary as JSON."
    ),
    log_level: str = typer.Option("INFO", "--log-level"),
) -> None:
    """Print descriptive summaries of every table."""
    configure_logging(log_level)
    from edutrace.analytics import load_dataset_from_disk, summarise_tables

    try:
        tables = load_dataset_from_disk(input)
    except FileNotFoundError as exc:
        _fail(str(exc), code=2)

    summary = summarise_tables(tables, max_categorical=max_categorical)

    for name, info in sorted(summary.items()):
        console.rule(
            f"[bold]{name}[/bold]  "
            f"({info['row_count']:,} rows, {info['column_count']} cols)"
        )
        for col, cinfo in info["columns"].items():
            kind = cinfo.get("kind", "?")
            if kind == "numeric":
                console.print(
                    f"  [cyan]{col}[/cyan]: mean={cinfo['mean']:.3f} "
                    f"min={cinfo['min']:.3f} max={cinfo['max']:.3f} "
                    f"nulls={cinfo['null_count']}"
                )
            elif kind == "string":
                top = ", ".join(
                    f"{t['value']}({t['count']})"
                    for t in cinfo.get("top", [])[:3]
                )
                console.print(
                    f"  [cyan]{col}[/cyan]: distinct={cinfo['distinct']} "
                    f"top=[{top}]"
                )
            elif kind == "datetime":
                console.print(
                    f"  [cyan]{col}[/cyan]: "
                    f"{cinfo.get('min')} → {cinfo.get('max')}"
                )
            elif kind == "boolean":
                console.print(
                    f"  [cyan]{col}[/cyan]: true={cinfo['true_count']} "
                    f"nulls={cinfo['null_count']}"
                )

    if json_out:
        json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        console.print(f"[green]JSON summary → {json_out}[/green]")


@app.command()
def export(
    input: Path = typer.Option(
        ..., "--input", "-i", help="Directory containing Parquet tables."
    ),
    format: list[str] = typer.Option(
        ["csv"], "--format", "-f", help="Target format(s); repeatable."
    ),
    compression: str = typer.Option(
        "zstd", "--compression", help="Compression for parquet re-writes."
    ),
    row_group_size: int = typer.Option(
        200_000, "--row-group-size", help="Row group size for parquet re-writes."
    ),
    log_level: str = typer.Option("INFO", "--log-level"),
) -> None:
    """Re-export an existing Parquet dataset to additional formats."""
    configure_logging(log_level)
    from edutrace.pipeline.export_manager import export_formats

    try:
        written = export_formats(  # type: ignore[arg-type]
            input,
            format,
            compression=compression,
            row_group_size=row_group_size,
        )
    except EduTraceError as exc:
        _fail(str(exc), code=1)
    console.print(f"[green]Wrote {len(written)} file(s).[/green]")


@app.command()
def verify(
    config: Path = typer.Option(
        ..., "--config", "-c", help="Config to verify for reproducibility."
    ),
    log_level: str = typer.Option("INFO", "--log-level"),
) -> None:
    """Run the pipeline twice under temp dirs and compare stable table hashes.

    File checksums are not compared — Parquet metadata and row-group
    boundaries differ run to run even for logically identical data. We
    compare a stable row hash per table instead.
    """
    configure_logging(log_level)
    cfg = _load_config_or_die(
        config,
        seed=None,
        output=None,
        learners=None,
        years=None,
        chunk_size=None,
        formats=None,
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)

        def run_one(tag: str) -> dict[str, str]:
            run_cfg = apply_overrides(
                cfg, {"output_directory": str(tmp_p / tag)}
            )
            run_cfg.pipeline.checkpoint.directory = str(tmp_p / f"ckpt_{tag}")
            run_cfg.pipeline.checkpoint.enabled = False
            orchestrator = Orchestrator(
                config=run_cfg, resume=False, reset_checkpoint=True
            )
            orchestrator.run()
            return _table_hashes(orchestrator.tables)

        console.print("[yellow]Run A...[/yellow]")
        hashes_a = run_one("run_a")
        console.print("[yellow]Run B...[/yellow]")
        hashes_b = run_one("run_b")

    diffs: list[str] = []
    if set(hashes_a) != set(hashes_b):
        diffs.append(f"table sets differ: {set(hashes_a) ^ set(hashes_b)}")
    for name in sorted(set(hashes_a) & set(hashes_b)):
        if hashes_a[name] != hashes_b[name]:
            diffs.append(f"{name}: hash mismatch")

    if not diffs:
        console.print("[green]Reproducible: all table hashes match.[/green]")
    else:
        console.print("[red]Non-reproducible differences:[/red]")
        for d in diffs[:20]:
            console.print(f"  • {d}")
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Print the current version."""
    console.print(f"EduTrace-Open {__version__}")


def main() -> None:  # pragma: no cover - convenience for console_scripts
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
