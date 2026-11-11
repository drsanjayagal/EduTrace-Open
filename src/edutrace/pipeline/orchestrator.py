"""End-to-end pipeline orchestrator.

The orchestrator drives every generator in dependency order, chunking the
stochastic tables by learner, checkpointing between safe boundaries, and
writing all outputs plus the manifest.

Design commitments
------------------
* Learners are sorted by ``learner_id`` before chunking.
* Enrolments are sorted by ``(learner_id, enrolment_id)`` before chunking.
* A learner's enrolments are never split across chunks.
* ID counters chain across chunks via the checkpoint state so that
  resuming does not renumber.
* On a successful run, the manifest is written and all file checksums are
  recorded.
* When ``_use_spill()`` returns True, chunk-level outputs are written to
  per-chunk Parquet files under ``checkpoints/spill/`` and later
  consolidated with ``sink_parquet``. Otherwise the in-memory path is used.

Resume semantics
----------------
When the checkpoint says a table is complete, the orchestrator
*reloads that table from disk* rather than skipping generation and then
failing on a subsequent ``self._tables[table]`` lookup. If the file is
absent for any reason, the checkpoint entry is discarded and the table is
regenerated.

Public API
----------
* :class:`Orchestrator` — configurable entry point.
* :func:`run_pipeline` — one-shot convenience wrapper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

from edutrace.config import EduTraceConfig
from edutrace.exceptions import PipelineError
from edutrace.generators import (
    generate_assessment_items,
    generate_attempts_for_chunk,
    generate_courses,
    generate_curriculum_dependencies,
    generate_digital_access,
    generate_enrolments,
    generate_feedback_for_chunk,
    generate_institutions,
    generate_learners,
    generate_learning_events_for_chunk,
    generate_modules,
    generate_programmes,
    generate_progression_events,
    generate_resources,
    generate_support_events,
    generate_weekly_engagement,
    populate_enrolment_outcomes,
)
from edutrace.logging_config import get_logger
from edutrace.pipeline.checkpoint import CheckpointManager
from edutrace.pipeline.chunk_writer import ChunkWriter
from edutrace.pipeline.manifest import (
    build_manifest,
    write_checksums,
    write_manifest,
    write_schema_manifest,
)
from edutrace.schemas.tables import ALL_TABLES
from edutrace.simulation.behavioural_models import (
    LearnerBehaviour,
    build_learner_behaviours,
)
from edutrace.utils.dates import AcademicCalendar
from edutrace.utils.ids import parse_id
from edutrace.utils.memory import estimate_learning_event_bytes, format_bytes
from edutrace.utils.random_state import RandomStateManager

_log = get_logger(__name__)


_LEARNING_EVENT_SCHEMA: dict[str, Any] = {
    "event_id": pl.Utf8,
    "learner_id": pl.Utf8,
    "enrolment_id": pl.Utf8,
    "course_id": pl.Utf8,
    "module_id": pl.Utf8,
    "resource_id": pl.Utf8,
    "event_timestamp": pl.Datetime("us"),
    "event_type": pl.Utf8,
    "event_duration_seconds": pl.Int64,
    "interaction_channel": pl.Utf8,
    "completion_flag": pl.Boolean,
    "event_sequence": pl.Int64,
}
_ASSESSMENT_ATTEMPT_SCHEMA: dict[str, Any] = {
    "attempt_id": pl.Utf8,
    "learner_id": pl.Utf8,
    "enrolment_id": pl.Utf8,
    "assessment_item_id": pl.Utf8,
    "attempt_number": pl.Int64,
    "attempt_timestamp": pl.Datetime("us"),
    "score": pl.Float64,
    "maximum_score": pl.Float64,
    "duration_seconds": pl.Int64,
    "submission_status": pl.Utf8,
    "late_submission_flag": pl.Boolean,
}
_FEEDBACK_EVENT_SCHEMA: dict[str, Any] = {
    "feedback_id": pl.Utf8,
    "attempt_id": pl.Utf8,
    "learner_id": pl.Utf8,
    "feedback_timestamp": pl.Datetime("us"),
    "feedback_type": pl.Utf8,
    "feedback_delay_hours": pl.Float64,
    "feedback_viewed": pl.Boolean,
    "revision_flag": pl.Boolean,
}


@dataclass
class Orchestrator:
    """Run every generator in dependency order and produce all outputs."""

    config: EduTraceConfig
    resume: bool = True
    reset_checkpoint: bool = False

    _rng: RandomStateManager = field(init=False)
    _checkpoint: CheckpointManager = field(init=False)
    _writer: ChunkWriter = field(init=False)
    _tables: dict[str, pl.DataFrame] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._rng = RandomStateManager(seed=self.config.project.random_seed)
        ckpt_dir = self.config.pipeline.checkpoint.directory
        self._checkpoint = CheckpointManager(ckpt_dir, self.config)
        if self.reset_checkpoint:
            self._checkpoint.reset()
        if not self.resume:
            self._checkpoint.reset()
        self._checkpoint.ensure_compatible()
        self._writer = ChunkWriter(self.config)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self) -> dict[str, Any]:
        """Execute the full pipeline. Returns the manifest."""
        self._preflight()
        self._generate_structural()
        self._generate_stochastic()
        self._generate_post_hoc()
        self._write_all()
        manifest = self._finalise_manifest()

        if self.config.validation.enabled:
            from edutrace.validation import run_validation

            _log.info("Running validation")
            report = run_validation(
                self._tables,
                self.config,
                write_report_to=(
                    Path(self.config.output.directory)
                    / "validation"
                    / "validation_report.json"
                ),
            )
            _log.info(
                "Validation: %d passed, %d failed, %d skipped",
                len(report.passed),
                len(report.failures),
                len(report.skipped),
            )
            if self.config.validation.strict:
                report.raise_if_failed()

        _log.info(
            "Pipeline complete. Manifest at %s", self.config.output.directory
        )
        return manifest

    @property
    def tables(self) -> dict[str, pl.DataFrame]:
        return self._tables

    # ------------------------------------------------------------------
    # Preflight
    # ------------------------------------------------------------------

    def _preflight(self) -> None:
        estimate = estimate_learning_event_bytes(
            num_learners=self.config.generation.num_learners,
            mean_events_per_learner_week=(
                self.config.generation.mean_events_per_learner_week
            ),
            weeks_per_semester=self.config.generation.weeks_per_semester,
            semesters=(
                self.config.generation.num_academic_years
                * self.config.generation.semesters_per_year
            ),
        )
        _log.info(
            "Estimated learning_event peak memory: %s", format_bytes(estimate)
        )
        _log.info(
            "Learners=%d, programmes=%d, courses/programme=%d, modules/course=%d",
            self.config.generation.num_learners,
            self.config.generation.num_programmes,
            self.config.generation.num_courses_per_programme,
            self.config.generation.num_modules_per_course,
        )

    # ------------------------------------------------------------------
    # Structural tables
    # ------------------------------------------------------------------

    def _generate_structural(self) -> None:
        cfg = self.config
        rng = self._rng

        self._ensure(
            "institution",
            lambda: generate_institutions(cfg, rng),
        )
        self._ensure(
            "programme",
            lambda: generate_programmes(cfg, rng, self._tables["institution"]),
        )
        self._ensure(
            "course",
            lambda: generate_courses(cfg, rng, self._tables["programme"]),
        )
        self._ensure(
            "module",
            lambda: generate_modules(cfg, rng, self._tables["course"]),
        )
        self._ensure(
            "curriculum_dependency",
            lambda: generate_curriculum_dependencies(
                cfg, rng, self._tables["module"], self._tables["course"]
            ),
        )
        self._ensure(
            "learner",
            lambda: generate_learners(cfg, rng, self._tables["programme"]),
        )
        self._ensure(
            "enrolment",
            lambda: generate_enrolments(
                cfg, rng, self._tables["learner"], self._tables["course"]
            ),
        )
        self._ensure(
            "learning_resource",
            lambda: generate_resources(cfg, rng, self._tables["module"]),
        )
        self._ensure(
            "assessment_item",
            lambda: generate_assessment_items(cfg, rng, self._tables["module"]),
        )
        self._ensure(
            "digital_access",
            lambda: generate_digital_access(cfg, rng, self._tables["learner"])[0],
        )

    # ------------------------------------------------------------------
    # Stochastic tables (chunked by learner)
    # ------------------------------------------------------------------

    def _generate_stochastic(self) -> None:
        cfg = self.config
        rng = self._rng
        calendar = self._calendar()

        learners = self._tables["learner"]
        enrolments = self._tables["enrolment"]
        if learners.is_empty() or enrolments.is_empty():
            for table in ("learning_event", "assessment_attempt", "feedback_event"):
                self._tables[table] = _empty_events_table(table)
                self._done_mark(table)
            return

        learners_sorted = learners.sort("learner_id")
        enrolments_sorted = enrolments.sort(["learner_id", "enrolment_id"])
        behaviours = self._build_behaviours(learners_sorted)
        chunk_size = max(1, cfg.pipeline.chunk_size)
        learner_ids = learners_sorted["learner_id"].to_list()
        n_chunks = (len(learner_ids) + chunk_size - 1) // chunk_size

        run_events = not self._done("learning_event")
        run_attempts = not self._done("assessment_attempt")
        run_feedback = not self._done("feedback_event")
        if not (run_events or run_attempts or run_feedback):
            _log.info("All stochastic tables already completed; skipping.")
            # Reload from disk if the caller needs the DataFrames later.
            self._reload_if_done("learning_event")
            self._reload_if_done("assessment_attempt")
            self._reload_if_done("feedback_event")
            return

        from edutrace.generators.attempt import build_attempt_indexes
        from edutrace.generators.learning_event import build_resource_index

        resource_index = build_resource_index(self._tables["learning_resource"])
        attempt_indexes = build_attempt_indexes(
            learners_sorted,
            self._tables["module"],
            self._tables["assessment_item"],
        )

        use_spill = self._use_spill()
        spill = self._spill_manager() if use_spill else None
        _log.info(
            "Stochastic generation: %d chunks, spill=%s, chunk_size=%d",
            n_chunks,
            use_spill,
            chunk_size,
        )

        events_parts: list[pl.DataFrame] = []
        attempts_parts: list[pl.DataFrame] = []
        feedback_parts: list[pl.DataFrame] = []

        next_event_id = self._checkpoint.next_id("learning_event", 1)
        next_attempt_id = self._checkpoint.next_id("assessment_attempt", 1)
        next_feedback_id = self._checkpoint.next_id("feedback_event", 1)

        for chunk_idx in range(n_chunks):
            start = chunk_idx * chunk_size
            end = min(start + chunk_size, len(learner_ids))
            chunk_learner_ids = learner_ids[start:end]
            chunk_enr = enrolments_sorted.filter(
                pl.col("learner_id").is_in(chunk_learner_ids)
            )
            if chunk_enr.is_empty():
                continue

            _log.info(
                "Chunk %d/%d: learners %d..%d (%d enrolment rows)",
                chunk_idx + 1,
                n_chunks,
                start,
                end - 1,
                chunk_enr.height,
            )

            if run_events:
                ev_df, next_event_id = generate_learning_events_for_chunk(
                    cfg,
                    rng,
                    chunk_enr,
                    self._tables["learning_resource"],
                    behaviours,
                    calendar,
                    event_id_start=next_event_id,
                    indexes={"resources_by_module": resource_index},
                )
                if spill is not None:
                    spill.write_chunk("learning_event", chunk_idx, ev_df)
                    self._checkpoint.record_chunk_file(
                        "learning_event",
                        str(spill.chunk_path("learning_event", chunk_idx)),
                    )
                else:
                    events_parts.append(ev_df)

            if run_attempts:
                at_df, next_attempt_id = generate_attempts_for_chunk(
                    cfg,
                    rng,
                    chunk_enr,
                    self._tables["assessment_item"],
                    self._tables["module"],
                    learners_sorted,
                    calendar,
                    attempt_id_start=next_attempt_id,
                    indexes=attempt_indexes,
                )
                if spill is not None:
                    spill.write_chunk("assessment_attempt", chunk_idx, at_df)
                    self._checkpoint.record_chunk_file(
                        "assessment_attempt",
                        str(spill.chunk_path("assessment_attempt", chunk_idx)),
                    )
                else:
                    attempts_parts.append(at_df)
            else:
                at_df = _empty_events_table("assessment_attempt")

            if run_feedback:
                fb_df, next_feedback_id = generate_feedback_for_chunk(
                    cfg,
                    rng,
                    at_df,
                    learners_sorted,
                    feedback_id_start=next_feedback_id,
                )
                if spill is not None:
                    spill.write_chunk("feedback_event", chunk_idx, fb_df)
                    self._checkpoint.record_chunk_file(
                        "feedback_event",
                        str(spill.chunk_path("feedback_event", chunk_idx)),
                    )
                else:
                    feedback_parts.append(fb_df)

            self._checkpoint.set_next_id("learning_event", next_event_id)
            self._checkpoint.set_next_id("assessment_attempt", next_attempt_id)
            self._checkpoint.set_next_id("feedback_event", next_feedback_id)

        if run_events:
            if spill is not None:
                self._tables["learning_event"] = self._consolidate_or_read(
                    spill, "learning_event", _LEARNING_EVENT_SCHEMA
                )
            else:
                self._tables["learning_event"] = (
                    pl.concat(events_parts)
                    if events_parts
                    else _empty_events_table("learning_event")
                )
            self._done_mark("learning_event")
        else:
            self._reload_if_done("learning_event")

        if run_attempts:
            if spill is not None:
                self._tables["assessment_attempt"] = self._consolidate_or_read(
                    spill, "assessment_attempt", _ASSESSMENT_ATTEMPT_SCHEMA
                )
            else:
                self._tables["assessment_attempt"] = (
                    pl.concat(attempts_parts)
                    if attempts_parts
                    else _empty_events_table("assessment_attempt")
                )
            self._done_mark("assessment_attempt")
        else:
            self._reload_if_done("assessment_attempt")

        if run_feedback:
            if spill is not None:
                self._tables["feedback_event"] = self._consolidate_or_read(
                    spill, "feedback_event", _FEEDBACK_EVENT_SCHEMA
                )
            else:
                self._tables["feedback_event"] = (
                    pl.concat(feedback_parts)
                    if feedback_parts
                    else _empty_events_table("feedback_event")
                )
            self._done_mark("feedback_event")
        else:
            self._reload_if_done("feedback_event")

        if spill is not None:
            spill.cleanup()

    def _consolidate_or_read(
        self,
        spill,
        table: str,
        schema: dict[str, Any],
    ) -> pl.DataFrame:
        """If a consolidated file exists in the output dir, read it;
        otherwise consolidate spilled chunks. Returns the DataFrame."""
        final_path = self._writer.path_for(table, self.config.output.formats[0])
        if final_path.exists():
            if final_path.suffix == ".parquet":
                return pl.read_parquet(final_path)
            return pl.read_csv(final_path)
        spill.consolidate(table, final_path, empty_schema=schema)
        if final_path.suffix == ".parquet":
            return pl.read_parquet(final_path)
        return _empty_events_table(table)

    # ------------------------------------------------------------------
    # Post-hoc enrichment
    # ------------------------------------------------------------------

    def _generate_post_hoc(self) -> None:
        cfg = self.config
        rng = self._rng

        if not self._done("_enrolment_outcomes"):
            _log.info("Populating enrolment outcomes")
            self._tables["enrolment"] = populate_enrolment_outcomes(
                cfg,
                self._tables["enrolment"],
                self._tables["assessment_attempt"],
                self._tables["assessment_item"],
            )
            self._done_mark("_enrolment_outcomes")

        if not self._done("weekly_engagement"):
            weekly_df, _ = generate_weekly_engagement(
                cfg,
                rng,
                self._tables["learning_event"],
                self._tables["enrolment"],
            )
            self._tables["weekly_engagement"] = weekly_df
            self._done_mark("weekly_engagement")
        else:
            self._reload_if_done("weekly_engagement")

        if not self._done("progression_event"):
            prog_df, _ = generate_progression_events(
                cfg,
                rng,
                self._tables["learner"],
                self._tables["enrolment"],
                self._tables["course"],
                self._tables["programme"],
            )
            self._tables["progression_event"] = prog_df
            self._done_mark("progression_event")
        else:
            self._reload_if_done("progression_event")

        if not self._done("support_event"):
            sup_df, _ = generate_support_events(
                cfg,
                rng,
                self._tables["learner"],
                self._tables["weekly_engagement"],
                self._tables["assessment_attempt"],
                self._tables["enrolment"],
                self._tables["assessment_item"],
            )
            self._tables["support_event"] = sup_df
            self._done_mark("support_event")
        else:
            self._reload_if_done("support_event")

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def _write_all(self) -> None:
        schema_tables = [t.name for t in ALL_TABLES]
        for table in schema_tables:
            df = self._tables.get(table)
            if df is None:
                raise PipelineError(f"Table {table} not generated before write")
            self._writer.write_table(table, df)

    def _finalise_manifest(self) -> dict[str, Any]:
        manifest_tables = {
            name: df for name, df in self._tables.items() if not name.startswith("_")
        }
        manifest = build_manifest(
            self.config,
            manifest_tables,
            self._writer.written_files,
            root=self.config.output.directory,
        )
        write_manifest(manifest, self.config.output.directory)
        write_checksums(manifest, self.config.output.directory)
        write_schema_manifest(manifest, self.config.output.directory)
        return manifest

    # ------------------------------------------------------------------
    # Resume / ensure helpers
    # ------------------------------------------------------------------

    def _ensure(self, table: str, generate_fn) -> None:
        """Ensure ``self._tables[table]`` is populated.

        If the checkpoint says the table is done AND the parquet file exists
        on disk, load it. Otherwise run ``generate_fn`` and populate.
        The checkpoint entry is marked done only *after* the table is in
        ``self._tables``; the write to disk happens later in ``_write_all``.
        A failed run therefore cannot leave a dangling "done" entry, because
        the checkpoint is reset on any non-resume run and because a later
        resume reloads from disk.
        """
        if self._done(table):
            loaded = self._try_load_from_disk(table)
            if loaded is not None:
                self._tables[table] = loaded
                return
            _log.warning(
                "Checkpoint says %s is done but no file was found; regenerating",
                table,
            )
        self._tables[table] = generate_fn()
        self._done_mark(table)

    def _try_load_from_disk(self, table: str) -> pl.DataFrame | None:
        path = self._writer.path_for(table, self.config.output.formats[0])
        if not path.exists():
            return None
        if path.suffix == ".parquet":
            return pl.read_parquet(path)
        if path.suffix == ".csv":
            return pl.read_csv(path)
        return None

    def _reload_if_done(self, table: str) -> None:
        if table in self._tables:
            return
        loaded = self._try_load_from_disk(table)
        if loaded is not None:
            self._tables[table] = loaded

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calendar(self) -> AcademicCalendar:
        return AcademicCalendar(
            start=date.fromisoformat(self.config.generation.academic_calendar_start),
            semesters_per_year=self.config.generation.semesters_per_year,
            weeks_per_semester=self.config.generation.weeks_per_semester,
            num_academic_years=self.config.generation.num_academic_years,
        )

    def _build_behaviours(
        self, learners_sorted: pl.DataFrame
    ) -> dict[int, LearnerBehaviour]:
        learner_keys = [
            parse_id(lid)[1] for lid in learners_sorted["learner_id"].to_list()
        ]
        behaviours_list = build_learner_behaviours(
            learner_keys=learner_keys,
            prepared=learners_sorted["baseline_preparedness"].to_list(),
            engagement=learners_sorted["initial_engagement_profile"].to_list(),
            preference=learners_sorted["synthetic_learning_preference"].to_list(),
            mean_events_per_learner_week=(
                self.config.generation.mean_events_per_learner_week
            ),
        )
        return {b.learner_key: b for b in behaviours_list}

    def _use_spill(self) -> bool:
        cfg = self.config.generation
        if cfg.num_learners >= 50_000:
            return True
        est_bytes = estimate_learning_event_bytes(
            num_learners=cfg.num_learners,
            mean_events_per_learner_week=cfg.mean_events_per_learner_week,
            weeks_per_semester=cfg.weeks_per_semester,
            semesters=cfg.num_academic_years * cfg.semesters_per_year,
        )
        return est_bytes > 2_000_000_000

    def _spill_manager(self):
        from edutrace.pipeline.streaming import SpillManager

        return SpillManager(
            self._checkpoint,
            compression=self.config.output.compression,
            row_group_size=self.config.output.row_group_size,
        )

    def _done(self, table: str) -> bool:
        return self._checkpoint.is_completed(table)

    def _done_mark(self, table: str) -> None:
        self._checkpoint.mark_completed(table)


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------


def run_pipeline(
    config: EduTraceConfig,
    *,
    resume: bool = True,
    reset_checkpoint: bool = False,
) -> dict[str, Any]:
    """Run the full pipeline once and return the manifest."""
    orchestrator = Orchestrator(
        config=config, resume=resume, reset_checkpoint=reset_checkpoint
    )
    return orchestrator.run()


def _empty_events_table(name: str) -> pl.DataFrame:
    schema_map = {
        "learning_event": _LEARNING_EVENT_SCHEMA,
        "assessment_attempt": _ASSESSMENT_ATTEMPT_SCHEMA,
        "feedback_event": _FEEDBACK_EVENT_SCHEMA,
    }
    if name not in schema_map:
        raise PipelineError(f"No empty schema for table {name!r}")
    return pl.DataFrame(schema=schema_map[name])
