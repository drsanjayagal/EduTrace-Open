# Performance

This document reports **measured** performance from runs executed in the
release environment. Where a value was not captured, the table says
"not measured" rather than an estimate. Do not add numbers to this file
without having actually run the configuration in question.

## Environment

- **OS:** Windows 11 (Build 26100)
- **CPU:** Intel Core i3-9100T (4 cores, 3.10 GHz)
- **RAM:** 11 GB total
- **Python:** 3.12.x (venv, dependencies per `requirements.txt`)
- **Storage:** SSD

All measurements below are from this machine. Your hardware will differ.

## Measured results

| Profile | Learners | Learning events | Total rows | Validation | Reproducible | Wall time | Peak RAM |
|---|---|---|---|---|---|---|---|
| `pilot.yaml` | 200 | 47,567 | ~53,000 | 41 passed / 0 failed | Yes (2 runs) | ~60 s | not measured |
| `standard.yaml` | 10,000 | 9,159,592 | 10,599,943 | 42 passed / 0 failed | Yes (2 runs) | 37–38 min | not measured |
| `large.yaml` | 100,000 | — | — | — | — | **not executed** | — |

"Total rows" is the sum of row counts across all 16 tables. "Validation" counts
are the checks emitted by the built-in validator; the standard run has one more
check enabled (`statistical.row_counts`) than pilot.

### Verified by

- **Pilot:** `python -m edutrace generate --config configs/pilot.yaml --reset-checkpoint`
- **Standard:** `python -m edutrace generate --config configs/standard.yaml --reset-checkpoint`
- **Pilot reproducibility:** `python -m edutrace verify --config configs/pilot.yaml`
- **Standard reproducibility:** `python -m edutrace verify --config configs/standard.yaml`
  (two independent full-pipeline runs; `stable_frame_hash` matched on every table)

### Not verified

- **`large.yaml` (100,000 learners):** not executed end-to-end in the release
  environment. The spill path (`SpillManager`) is exercised at standard scale
  (`spill=True` in the run log) and by the test suite, but the profile itself
  has not been run to completion.
- **Peak RAM** on any profile: not captured. The pipeline logs an internal
  memory *estimate* (`Estimated learning_event peak memory: …`) but does not
  record actual usage.
- **Reproducibility at large scale:** not tested. The claim of reproducibility
  applies to pilot and standard scales only.
- **Cross-platform timings:** all measurements are from Windows 11. Linux and
  macOS have not been benchmarked.
- **JSONL export at scale:** not exercised on any profile beyond pilot.

## Time breakdown at standard scale

From the log of `standard.yaml` (40-minute run):

| Stage | Duration | % of total |
|---|---|---|
| `_generate_stochastic` (event generation) | ~37 min | 97 % |
| Spill consolidation | ~1 s | <0.1 % |
| `populate_enrolment_outcomes` | ~30 s | ~1.3 % |
| `_write_all` (Parquet + CSV) | ~30 s | ~1.3 % |
| Validation | ~13 s | ~0.5 % |
| Manifest finalisation | ~5 s | ~0.2 % |

**Event generation dominates runtime.** The generator builds every event row
in memory (as a Python dict) before writing the chunk to Parquet. Future
optimisation should focus here — per-learner-week batching would produce a
10–20× speedup. This is documented as a known limitation, not fixed.

## Memory considerations

The standard run estimates ~3.1 GiB peak for the `learning_event` table alone.
That estimate is internal to the pipeline; actual peak RAM was not captured.

**Practical warning.** During verification we observed that running
`standard.yaml` while PyCharm is open with its default 2 GB heap can exhaust
an 11 GB machine. If you run the standard profile on a similar machine:

- Run from an external PowerShell window (not PyCharm's terminal), or
- Increase PyCharm's heap via **Help → Edit Custom VM Options**
  (`-Xmx3072m` or `-Xmx3584m`), or
- Do not keep PyCharm open during the run.

The Python process alone needs roughly 3–4 GB at standard scale. Combined with
an IDE, the total can approach the limit of a small laptop.

## Recommendations by use case

| Use case | Recommended profile |
|---|---|
| Iterating on the code, writing tests | `pilot.yaml` (< 1 min) |
| Building research datasets, running analyses | `standard.yaml` (~40 min) |
| Publishing benchmark results | `standard.yaml` with `verify` |
| Very large synthetic cohorts (100k+) | `large.yaml` — **test on your hardware first** |

For the `large` profile, expect hours of wall time and tens of GB of disk
(Parquet + CSV). Verify the pipeline is stable on your machine by running
`standard.yaml` twice with `verify` before attempting `large.yaml`.

## Do not add unverified numbers

If you re-run on different hardware and want to update this file, replace a
"not measured" with the actual value **and add the machine specification to
the "Environment" section**. Numbers without the hardware they were measured
on are misleading.
