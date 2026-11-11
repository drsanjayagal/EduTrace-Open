from __future__ import annotations

from pathlib import Path

import pytest

from edutrace.config import EduTraceConfig, apply_overrides, load_config
from edutrace.exceptions import ConfigError


def test_load_config_pilot() -> None:
    cfg = load_config(Path("configs/pilot.yaml"))
    assert cfg.generation.profile == "pilot"
    assert cfg.generation.num_learners == 200


def test_load_config_defaults_match_schema():
    cfg = EduTraceConfig()
    assert cfg.generation.num_learners >= 1
    assert cfg.validation.check_primary_keys is True


def test_load_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "does_not_exist.yaml")


def test_load_config_malformed(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("not: [valid: yaml", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)


def test_apply_overrides():
    cfg = load_config("configs/pilot.yaml")
    new = apply_overrides(cfg, {"seed": 7, "num_learners": 42})
    assert new.project.random_seed == 7
    assert new.generation.num_learners == 42


def test_apply_overrides_unknown_key():
    cfg = EduTraceConfig()
    with pytest.raises(ConfigError):
        apply_overrides(cfg, {"nonsense": 1})
