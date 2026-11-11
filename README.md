
# EduTrace-Open

### A Synthetic Longitudinal Multimodal Dataset for Higher Education

**An Open Research Framework for Modelling Learning Activities, Assessment Interactions, and Educational Progression**

<p align="center">

  **Research | Synthetic Data | Learning Analytics | Educational Data Mining**

</p>

---

## Project Overview

EduTrace-Open is an open-source research framework designed to generate a synthetic longitudinal multimodal dataset representing learning activities, assessment interactions, academic engagement, and educational progression in higher education environments.

The framework aims to provide a reproducible, scalable, and privacy-preserving foundation for research in:

- Learning Analytics and Educational Data Mining
- Student Behaviour and Engagement Modelling
- Longitudinal Learning Pattern Analysis
- Predictive Modelling of Academic Progression
- Multimodal Educational Data Integration
- Synthetic Data Generation and Benchmarking

All generated records are entirely synthetic and do not represent actual students, individuals, or educational institutions.

---

## Project Information

| Attribute | Details |
|---|---|
| Project | EduTrace-Open |
| Author | Dr. Sanjay Agal |
| Affiliation | Parul Institute of Engineering and Technology, Parul University |
| Location | Vadodara, Gujarat, India |
| Development Status | Phase 1 Complete |
| Upcoming Development | Phases 2–11 |
| Source Code License | MIT |
| Data Classification | Fully Synthetic |

---

## Development Roadmap

| Phase | Development Area | Status |
|---|---|---|
| 1 | Repository Foundation and Core Infrastructure | Completed |
| 2 | Institutional and Academic Structure Generation | Pending |
| 3 | Learning Activity and Event Generation | Pending |
| 4 | Assessment and Interaction Generation | Pending |
| 5 | Multimodal Data Generation | Pending |
| 6 | Longitudinal Learning and Progression Modelling | Pending |
| 7 | Data Validation and Quality Assurance | Pending |
| 8 | Dataset Integration and Storage | Pending |
| 9 | Reproducibility and Benchmarking | Pending |
| 10 | Documentation and Research Artifacts | Pending |
| 11 | Packaging, Installation, and Release | Pending |

*The roadmap represents the planned development sequence.*

---

## Installation

**Status:** Planned for Phase 11.

### Development Environment

Create and activate a Python virtual environment:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

Install the project with development dependencies:

```bash
pip install -e ".[dev]"
```

---

# Phase 1 — Integration and Architecture Notes

## 1. Core Integration Contracts

The following interfaces have been established during Phase 1. They serve as integration contracts for subsequent development phases.

**Important:** Existing exported names and function interfaces should remain stable. Any modification must be reflected in all dependent modules and callers.

### 1.1 Core Infrastructure

| Module | Exported Interfaces | Primary Consumers |
|---|---|---|
| `constants` | `*Enum` classes, `ALL_EVENT_TYPES`, `DEFAULT_RANDOM_SEED` | Generators, schemas, validators |
| `exceptions` | `EduTraceError` and subclasses | Configuration, pipeline, validation, CLI |
| `logging_config` | `configure_logging`, `get_logger` | CLI, pipeline, all modules |
| `config` | `EduTraceConfig`, `load_config`, `apply_overrides`, `dump_config` | CLI, scripts, pipeline |

### 1.2 Utility Interfaces

| Module | Exported Interfaces | Primary Consumers |
|---|---|---|
| `utils.ids` | `format_id`, `format_ids`, `parse_id`, `PREFIX_*` | All generators |
| `utils.random_state` | `RandomStateManager`, `.table_rng`, `.row_rng`, `.spawn` | All generators |
| `utils.dates` | `AcademicCalendar`, `random_timestamp_within` | Temporal and longitudinal generators |
| `utils.hashing` | `stable_int_hash`, `sha256_file`, `sha256_bytes` | RNG, manifest, reproducibility |
| `utils.file_utils` | `ensure_dir`, `list_files`, `relative_to_root`, `file_size_bytes` | Storage, manifest |
| `utils.memory` | `estimate_learning_event_bytes`, `format_bytes` | CLI pre-flight checks |

### 1.3 Schema Interfaces

| Module | Exported Interfaces | Primary Consumers |
|---|---|---|
| `schemas.tables` | `ALL_TABLES`, `TABLE_SCHEMAS`, `get_schema`, `validate_row` | Validation, export, documentation |

---

## 2. Open Design Decisions

The following architectural decisions require confirmation before proceeding with Phase 2.

| No. | Design Decision | Current Implementation | Confirmation Required |
|---|---|---|---|
| 1 | Schema file organization | Consolidated into `schemas/tables.py` and `schemas/common.py` | Confirm consolidated structure or request a seven-file split |
| 2 | Academic year limit | `num_academic_years` capped at 10 in `GenerationConfig` | Confirm cap or request an uncapped configuration |
| 3 | Checkpoint granularity | `every_n_learners: 10000` in `default.yaml`; 1000 for pilot | Confirm default checkpoint interval |
| 4 | Academic calendar | Four-week inter-semester gap and 15-week semester | Confirm modelling assumptions |

### 2.1 Academic Calendar Assumptions

Current calendar configuration:

```python
INTERSEMESTER_GAP_WEEKS = 4
WEEKS_PER_SEMESTER = 15
```

These values represent the initial academic calendar modelling assumptions and may be adjusted according to the intended institutional calendar.

### 2.2 Deferred Configuration

The following constants have intentionally not been introduced during Phase 1:

```python
SCHEDULE_*
```

Scheduling weights will be defined in Phase 2 or Phase 3, once the corresponding generation logic and behavioural assumptions have been established.

---

## 3. Phase 2 — Planned Implementation

**Next Development Phase**

Phase 2 will establish the institutional and academic foundation of the synthetic dataset.

### 3.1 Planned Generator Modules

| Module | Responsibility |
|---|---|
| `generators/institution.py` | Generate synthetic institutional records |
| `generators/programme.py` | Generate academic programmes |
| `generators/course.py` | Generate course-level records |
| `generators/module.py` | Generate academic modules |
| `generators/curriculum.py` | Generate curriculum structures |
| `generators/learner.py` | Generate synthetic learner profiles |
| `generators/enrolment.py` | Generate learner enrolment records |
| `generators/__init__.py` | Expose generator interfaces |

### 3.2 Implementation Requirements

Each generator will follow a consistent functional architecture:

- Accept a `RandomStateManager` instance.
- Receive the relevant configuration slice.
- Consume upstream generated tables where dependencies exist.
- Return a Polars DataFrame.
- Conform exactly to the established table schema.
- Maintain deterministic and reproducible generation.
- Avoid introducing unnecessary dependencies.

### 3.3 Expected Generator Pattern

```python
def generate_entity(
    random_state,
    config,
    upstream_tables=None,
):
    """
    Generate a synthetic entity table.

    Returns:
        pl.DataFrame: Generated records
    """
    ...
```

The actual function signatures will be aligned with the existing configuration and schema contracts.

---

## 4. Development Principles

All subsequent development should adhere to the following principles:

1. **Synthetic by Design:** No real student or institutional records.
2. **Reproducibility:** Consistent outputs under controlled random seeds.
3. **Modularity:** Independent, reusable generation components.
4. **Schema Consistency:** Strict adherence to predefined table schemas.
5. **Scalability:** Support for large-scale longitudinal datasets.
6. **Privacy Preservation:** No dependency on personally identifiable educational records.
7. **Scientific Integrity:** Explicit modelling assumptions and transparent data-generation procedures.
8. **Backward Compatibility:** Preserve established integration interfaces.

---

## 5. Project Continuation Protocol

Before starting Phase 2, the following decisions should be confirmed:

- Schema organization.
- Maximum academic years.
- Default checkpoint interval.
- Academic calendar assumptions.

Once confirmed, development can proceed with the institutional and academic structure generators.

### Available Actions

| Command | Description |
|---|---|
| `CONTINUE` | Proceed with Phase 2 implementation. |
| `AUDIT` | Inspect Phase 1 implementation for architectural consistency, interface correctness, and potential integration issues. |
| `CUSTOMIZE` | Specify changes to any of the four open design decisions before implementation. |

**Audit limitation:** An architectural inspection does not constitute a claim of successful execution or testing.

---

## 6. Author and Research Affiliation

**Dr. Sanjay Agal**  
Professor & Head  
Department of Artificial Intelligence and Data Science  
Parul Institute of Engineering and Technology  
Parul University  
Vadodara, Gujarat, India

---

## 7. License and Data Usage

The source code is distributed under the **MIT License**.

All datasets generated through EduTrace-Open are fully synthetic. They are intended exclusively for research, experimentation, educational data mining, machine learning development, and benchmarking.

The generated records do not represent real individuals or actual educational institutions.

---

<p align="center">

**EduTrace-Open**

*Building Reproducible Synthetic Educational Data Infrastructure for Research in Learning Analytics and Artificial Intelligence.*

</p>
