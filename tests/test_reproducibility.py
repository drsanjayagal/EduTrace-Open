from __future__ import annotations

from edutrace.generators import generate_institutions, generate_programmes
from edutrace.utils.hashing import stable_frame_hash
from edutrace.utils.random_state import RandomStateManager


def test_same_seed_same_institutions(tiny_config):
    rng_a = RandomStateManager(seed=777)
    rng_b = RandomStateManager(seed=777)
    a = generate_institutions(tiny_config, rng_a)
    b = generate_institutions(tiny_config, rng_b)
    assert stable_frame_hash(a) == stable_frame_hash(b)


def test_different_seed_different_output(tiny_config):
    rng_a = RandomStateManager(seed=1)
    rng_b = RandomStateManager(seed=2)
    a = generate_institutions(tiny_config, rng_a)
    b = generate_institutions(tiny_config, rng_b)
    # Only one institution by default; outputs may coincide on `region` etc.
    # Compare the whole frames' hashes — institution type/region should vary
    # with overwhelming probability.
    assert stable_frame_hash(a) != stable_frame_hash(b)


def test_programmes_deterministic(tiny_config):
    rng_a = RandomStateManager(seed=42)
    rng_b = RandomStateManager(seed=42)
    inst_a = generate_institutions(tiny_config, rng_a)
    inst_b = generate_institutions(tiny_config, rng_b)
    prog_a = generate_programmes(tiny_config, rng_a, inst_a)
    prog_b = generate_programmes(tiny_config, rng_b, inst_b)
    assert stable_frame_hash(prog_a) == stable_frame_hash(prog_b)
