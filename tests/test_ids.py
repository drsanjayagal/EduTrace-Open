from __future__ import annotations

import numpy as np
import pytest

from edutrace.utils.ids import (
    PREFIX_LEARNER,
    format_id,
    format_ids,
    parse_id,
    row_key_from_ints,
)


def test_format_id_round_trip():
    assert format_id(PREFIX_LEARNER, 42) == "lrn_00000042"
    prefix, n = parse_id("lrn_00000042")
    assert prefix == "lrn"
    assert n == 42


def test_format_id_rejects_negative():
    with pytest.raises(ValueError):
        format_id(PREFIX_LEARNER, -1)


def test_format_ids_vector():
    ids = format_ids(PREFIX_LEARNER, np.array([1, 2, 3]))
    assert list(ids) == ["lrn_00000001", "lrn_00000002", "lrn_00000003"]


def test_parse_id_rejects_invalid():
    with pytest.raises(ValueError):
        parse_id("nope")
    with pytest.raises(ValueError):
        parse_id("lrn_abc")


def test_row_key_from_ints_unique_and_bounded():
    keys = set()
    for a in range(5):
        for b in range(5):
            for c in range(5):
                keys.add(row_key_from_ints(a, b, c))
    assert len(keys) == 125  # all unique


def test_row_key_rejects_out_of_bound():
    with pytest.raises(ValueError):
        row_key_from_ints(-1)
