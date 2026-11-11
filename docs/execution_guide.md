# Execution Guide

The commands below have been executed end-to-end in the release environment
(Windows 11, Python 3.12.x, dependencies per `requirements.txt`). Wall times
are recorded from actual runs in [performance.md](performance.md).

The `large` profile (`configs/large.yaml`) is **not verified end-to-end** in
the release environment. Treat it as untested code — run it on your own
hardware before relying on it.

## Expected runtime

| Profile | Learners | Expected wall time | Peak RAM |
|---|---|---|---|
| `pilot.yaml` | 200 | under 1 minute | ~200 MB |
| `standard.yaml` | 10,000 | 37–40 minutes | ~3–4 GB |
| `large.yaml` | 100,000 | not verified | not verified |

If you run the standard profile on a small machine, do not keep PyCharm open
at the same time — the Python process and the IDE can exhaust an 11 GB laptop
together. Run generation from an external PowerShell window instead.

## Linux / macOS

```bash
# 1. Clone and enter the repo
git clone <repo-url> EduTrace-Open
cd EduTrace-Open

# 2. Create and activate a virtualenv
python3.12 -m venv .venv
source .venv/bin/activate

# 3. Install
pip install --upgrade pip
pip install -e ".[dev]"

# 4. Generate the pilot dataset
python -m edutrace generate --config configs/pilot.yaml

# 5. Inspect
python -m edutrace inspect --input data/generated

# 6. Validate (strict = exit non-zero on failure)
python -m edutrace validate --input data/generated --strict

# 7. Verify reproducibility (runs the pipeline twice)
python -m edutrace verify --config configs/pilot.yaml

# 8. Run the tests
python -m pytest -q

# 9. Lint
ruff check src tests scripts

# 10. Standard profile
python -m edutrace generate --config configs/standard.yaml --reset-checkpoint

# 11. Custom seed and output directory
python -m edutrace generate \
    --config configs/default.yaml \
    --seed 20261110 \
    --output data/generated_default \
    --learners 5000
