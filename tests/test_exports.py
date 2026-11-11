from __future__ import annotations

import polars as pl

from edutrace.pipeline.export_manager import export_formats


def test_parquet_csv_roundtrip(tmp_path):
    df = pl.DataFrame(
        {"a": [1, 2, 3], "b": ["x", "y", "z"], "c": [0.1, 0.2, 0.3]}
    )
    parquet_path = tmp_path / "t.parquet"
    df.write_parquet(parquet_path)

    written = export_formats(tmp_path, ["csv"])
    assert len(written) == 1
    assert written[0].suffix == ".csv"

    back = pl.read_csv(written[0])
    assert back.height == 3


def test_export_jsonl(tmp_path):
    df = pl.DataFrame({"a": [1, 2]})
    (tmp_path / "t.parquet").parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(tmp_path / "t.parquet")

    written = export_formats(tmp_path, ["jsonl"])
    assert len(written) == 1
    assert written[0].suffix == ".jsonl"
