# EduTrace-Open

A synthetic longitudinal multimodal dataset of learning activities,
assessment interactions, and educational progression in higher education.

**Status:** Phase 1 complete (repository foundation). Phases 2–11 pending.

**Author:** Dr. Sanjay Agal, Parul Institute of Engineering and Technology,
Parul University, Vadodara, Gujarat, India.

**License:** MIT for source code. All generated data is fully synthetic and
does not represent any real persons or institutions.

## Installation (placeholder for Phase 11)

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"


---

# Phase 1 — Integration notes

**Interfaces used by later phases (do not change without updating callers):**

| Module | Exported | Used by |
|---|---|---|
| `constants` | `*Enum` classes, `ALL_EVENT_TYPES`, `DEFAULT_RANDOM_SEED` | every generator, schema, validator |
| `exceptions` | `EduTraceError` + subclasses | config, pipeline, validation, CLI |
| `logging_config` | `configure_logging`, `get_logger` | CLI, pipeline, all modules |
| `config` | `EduTraceConfig`, `load_config`, `apply_overrides`, `dump_config` | CLI, scripts, pipeline |
| `utils.ids` | `format_id`, `format_ids`, `parse_id`, `PREFIX_*` | all generators |
| `utils.random_state` | `RandomStateManager` (`.table_rng`, `.row_rng`, `.spawn`) | all generators |
| `utils.dates` | `AcademicCalendar`, `random_timestamp_within` | temporal + longitudinal generators |
| `utils.hashing` | `stable_int_hash`, `sha256_file`, `sha256_bytes` | RNG, manifest, reproducibility |
| `utils.file_utils` | `ensure_dir`, `list_files`, `relative_to_root`, `file_size_bytes` | storage, manifest |
| `utils.memory` | `estimate_learning_event_bytes`, `format_bytes` | CLI pre-flight checks |
| `schemas.tables` | `ALL_TABLES`, `TABLE_SCHEMAS`, `get_schema`, `validate_row` | validation, export, docs |

**Open design decisions for you to confirm before Phase 2:**

1. **Schema file layout.** I consolidated into `schemas/tables.py` + `schemas/common.py` (see top of message). Confirm, or request the 7-file split.
2. **`num_academic_years` cap.** I capped at 10 in `GenerationConfig` as a sanity bound. Say if you want it uncapped.
3. **`pipeline.checkpoint.every_n_learners` default.** Set to 10 000 in `default.yaml`, 1 000 for pilot. Confirm this is the granularity you want, or specify differently.
4. **`INTERSEMESTER_GAP_WEEKS = 4`** and **`WEEKS_PER_SEMESTER = 15`** are the modelling assumptions for the calendar. Adjust if you have a different target calendar.
5. **Not included in Phase 1** (intentional): `constants.py` still needs `SCHEDULE_*` weights once generators exist; I'll extend it in Phase 2/3 rather than invent weights now.

**What Phase 2 will produce (next response):** `generators/institution.py`, `programme.py`, `course.py`, `module.py`, `curriculum.py`, `learner.py`, `enrolment.py` — each a pure function taking a `RandomStateManager` + config slice + upstream tables, returning a Polars DataFrame with the exact schema above, plus `generators/__init__.py` exposing them. No new dependencies.

Reply **`CONTINUE`** to proceed to Phase 2. Reply **`AUDIT`** to have me re-check Phase 1 code (I will not claim it as tested — only inspected). Reply with any of the confirmations above first if you want those decisions locked.
