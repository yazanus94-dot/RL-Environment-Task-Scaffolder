"""Shared fixtures for the scaffolder test suite."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

# The fixtures dir contains *task snapshots* whose embedded test files are
# intentionally broken (they are the RL task states) -- they must never be
# collected by the scaffolder's own test suite.
collect_ignore_glob = ["fixtures/*"]

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SNAPSHOTS = FIXTURES / "github_snapshots"


@pytest.fixture(scope="session")
def snapshots_root() -> Path:
    assert SNAPSHOTS.is_dir(), f"missing fixtures: {SNAPSHOTS}"
    return SNAPSHOTS


@pytest.fixture(scope="session")
def sample_snapshot(snapshots_root: Path) -> Path:
    return snapshots_root / "fix-percentile-boundary"


@pytest.fixture(scope="session")
def all_specs(snapshots_root: Path) -> Iterator[list]:
    from task_scaffolder import SnapshotExtractor

    yield list(SnapshotExtractor().extract_all(snapshots_root))
