"""Stable hashing helpers.

These are used for:
* Deriving deterministic seeds from strings.
* Producing file checksums for the manifest.
* Producing table-value hashes for the CLI's reproducibility verifier.

We deliberately avoid Python's built-in ``hash`` for seed derivation because
it is salted per process. ``hashlib.blake2b`` / ``sha256`` are fast and
process-stable.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def stable_int_hash(value: str, modulo: int = 2**32) -> int:
    """Return a stable, non-negative integer derived from ``value``."""
    if modulo <= 0:
        raise ValueError("modulo must be positive")
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % modulo


def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """Return the SHA-256 hex digest of a file, streamed in 1 MiB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest of a byte string."""
    return hashlib.sha256(data).hexdigest()


def stable_frame_hash(df: Any, *, sample: int | None = None) -> str:
    """Return a stable SHA-256 hex digest over a DataFrame's rows.

    Row order is sorted by all columns before hashing so the digest is
    invariant to how chunks were concatenated. Non-string values are
    stringified with their ``repr`` so datetime/float formatting is stable.
    ``sample`` limits the hash to the first N rows after sorting (useful
    for very large tables in the CLI).
    """
    if df is None:
        return hashlib.sha256(b"<none>").hexdigest()

    if df.height == 0:
        return hashlib.sha256(b"<empty>").hexdigest()

    sorted_df = df.sort(df.columns)
    if sample is not None and sorted_df.height > sample:
        sorted_df = sorted_df.head(sample)

    h = hashlib.sha256()
    h.update(b"|".join(str(c).encode("utf-8") for c in sorted_df.columns))
    for row in sorted_df.iter_rows():
        line = "|".join(repr(v) for v in row).encode("utf-8")
        h.update(line)
        h.update(b"\n")
    return h.hexdigest()
