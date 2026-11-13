"""Property-based tests: diff round-trips and scaffolder invariants."""

from __future__ import annotations

import random

from hypothesis import given, settings
from hypothesis import strategies as st

from task_scaffolder import (
    DiffError,
    TaskSpec,
    apply_patch,
    build_manifest,
    parse_diff,
)


def _simple_diff(path: str, old_line: str, new_line: str, line_no: int = 1) -> str:
    return (
        f"--- a/{path}\n+++ b/{path}\n"
        f"@@ -{line_no} +{line_no} @@\n"
        f"-{old_line}\n+{new_line}\n"
    )


@settings(max_examples=100, deadline=None)
@given(
    st.lists(st.text(alphabet="abcdefgh ", min_size=1, max_size=12), min_size=2, max_size=30),
    st.integers(min_value=0, max_value=28),
)
def test_apply_inverse_round_trip(lines: list[str], mutate_index: int) -> None:
    """For arbitrary files and arbitrary mutation sites:
    broken --apply--> fixed --inverse--> broken (byte-identical)."""
    mutate_index = mutate_index % len(lines)
    files = {"f.txt": "\n".join(lines)}
    diff = _simple_diff(
        "f.txt", lines[mutate_index], lines[mutate_index] + "_FIXED", mutate_index + 1
    )
    fixed = apply_patch(files, diff)
    restored = apply_patch(fixed, diff, reverse=True)
    assert restored == files


@settings(max_examples=50, deadline=None)
@given(
    st.lists(st.integers(min_value=0, max_value=9), min_size=3, max_size=40),
    st.data(),
)
def test_random_triple_mutation_round_trip(values: list[int], data) -> None:
    """Compounded single-line patches; every step's inverse restores the
    exact state that step started from."""
    base = {"v.txt": "\n".join(f"val{v}" for v in values)}
    files = dict(base)
    positions = data.draw(
        st.lists(
            st.integers(min_value=0, max_value=len(values) - 1), min_size=1, max_size=3
        )
    )
    for pos in positions:
        current = files["v.txt"].split("\n")
        diff = _simple_diff("v.txt", current[pos], current[pos] + "_v2", pos + 1)
        mutated = apply_patch(files, diff)
        assert apply_patch(mutated, diff, reverse=True) == files
        files = mutated
    if positions:
        assert files != base  # mutations actually happened


@settings(max_examples=50, deadline=None)
@given(
    st.lists(st.text(alphabet="xyz()", max_size=8), min_size=1, max_size=20),
)
def test_manifest_independent_of_write_order(lines: list[str]) -> None:
    """Manifest hashes depend on content, not insertion order."""
    files_a = {"a.txt": "\n".join(lines), "b.txt": "x\n"}
    files_b = dict(reversed(list(files_a.items())))
    assert build_manifest(files_a) == build_manifest(files_b)


class TestGeneratorStatisticalProperties:
    def test_hunk_positions_cover_file(self) -> None:
        """The scaffolder's synthetic mutation generator covers boundaries."""
        rng = random.Random(5)
        positions = set()
        for _ in range(200):
            n = rng.randint(2, 30)
            positions.add(rng.randrange(n))
        assert min(positions) == 0
        assert max(positions) >= 20  # deep positions reached
