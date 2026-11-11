from __future__ import annotations

import pytest

from edutrace.pipeline import Orchestrator, ensure_valid_order, topological_order
from edutrace.pipeline.dependency_manager import TABLE_DEPENDENCIES
from edutrace.schemas.tables import ALL_TABLES


def test_dependency_graph_covers_all_tables():
    assert set(TABLE_DEPENDENCIES.keys()) == {t.name for t in ALL_TABLES}


def test_topological_order_is_valid():
    order = topological_order()
    ensure_valid_order(order)


@pytest.mark.integration
def test_orchestrator_produces_all_tables(tiny_config, tmp_path):
    cfg = tiny_config.model_copy(deep=True)
    cfg.output.directory = str(tmp_path / "out")
    cfg.pipeline.checkpoint.directory = str(tmp_path / "ckpt")
    cfg.pipeline.checkpoint.enabled = True
    orch = Orchestrator(config=cfg, resume=False, reset_checkpoint=True)
    manifest = orch.run()

    assert set(manifest["tables"].keys()) == {t.name for t in ALL_TABLES}
    for name, info in manifest["tables"].items():
        assert info["row_count"] >= 0


@pytest.mark.integration
def test_orchestrator_resume(tiny_config, tmp_path):
    cfg = tiny_config.model_copy(deep=True)
    cfg.output.directory = str(tmp_path / "out")
    cfg.pipeline.checkpoint.directory = str(tmp_path / "ckpt")
    cfg.pipeline.checkpoint.enabled = True

    orch1 = Orchestrator(config=cfg, resume=False, reset_checkpoint=True)
    manifest1 = orch1.run()

    orch2 = Orchestrator(config=cfg, resume=True, reset_checkpoint=False)
    manifest2 = orch2.run()

    for name in manifest1["tables"]:
        assert manifest1["tables"][name]["row_count"] == manifest2["tables"][name]["row_count"]
