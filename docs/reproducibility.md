# Reproducibility

## What is guaranteed

Given identical `config.yaml` and `project.random_seed`, and identical `pipeline.chunk_size`, two runs of `python -m edutrace generate` produce **the same values in every table** *and* **the same identifiers** — except for fields that are derived from wall-clock time (only the manifest's `generated_at_utc`).

## What is not guaranteed across chunk-size changes

Changing `pipeline.chunk_size` changes the order in which learners are processed within a table, and therefore changes the ID counters assigned to events/attempts/feedback. **Values are unchanged; IDs are reassigned.** This is a documented property of the design.

If you need stable IDs across chunk-size variations, use a single chunk size throughout a study. The default is `50 000` for all profiles.

## Verification

```bash
python -m edutrace verify --config configs/pilot.yaml
