"""Reproducible benchmark for the scaffolder pipeline.

Measures:
1. Scaffolding throughput: tasks/second as snapshot size grows.
2. Diff-engine cost: apply/inverse cost vs file length and diff width.
3. Harness verification cost: real pytest subprocess runs per state.

Run: python benchmarks/benchmark.py
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from task_scaffolder import (  # noqa: E402
    SnapshotExtractor,
    apply_patch,
    scaffold,
    write_bundle,
)
from task_scaffolder.algorithms import parse_diff  # noqa: E402


def median_s(fn, *args, repeat: int = 5) -> float:
    samples = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn(*args)
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def bench_scaffold_throughput() -> list[dict[str, object]]:
    rows = []
    for n_lines in (100, 1_000, 5_000):
        # Synthetic snapshot: a file of n_lines with a one-line fix.
        base = {"mod.py": "\n".join(f"line_{i} = {i}" for i in range(n_lines))}
        diff = (
            "--- a/mod.py\n+++ b/mod.py\n"
            f"@@ -{n_lines // 2 + 1} +{n_lines // 2 + 1} @@\n"
            f"-line_{n_lines // 2} = {n_lines // 2}\n"
            f"+line_{n_lines // 2} = {n_lines // 2}  # fixed\n"
        )
        spec_name = f"synthetic-{n_lines}"

        def build_spec():
            return SnapshotExtractor(), None  # placeholder; direct TaskSpec below

        from task_scaffolder import TaskSpec  # noqa: PLC0415

        spec = TaskSpec(
            task_id=spec_name,
            base_files=base,
            solution_diff=diff,
            f2p_tests=("t1",),
            p2p_tests=(),
        )
        elapsed = median_s(scaffold, spec, repeat=5)
        rows.append({"file_lines": n_lines, "scaffold_s": elapsed})
    return rows


def bench_diff_engine() -> dict[str, object]:
    n = 10_000
    files = {"big.txt": "\n".join(f"row{i}" for i in range(n))}
    diff = (
        "--- a/big.txt\n+++ b/big.txt\n"
        f"@@ -{n} +{n} @@\n-row{n - 1}\n+row{n - 1}_fixed\n"
    )
    forward = median_s(apply_patch, files, diff, repeat=10)
    fixed = apply_patch(files, diff)
    backward = median_s(apply_patch, fixed, diff, True, repeat=10)
    parse = median_s(parse_diff, diff, repeat=10)
    return {
        "file_lines": n,
        "parse_s": parse,
        "forward_apply_s": forward,
        "inverse_apply_s": backward,
    }


def bench_harness_verification() -> dict[str, object]:
    """Cost of one full polarity check (real pytest subprocesses)."""
    snapshots = REPO_ROOT / "tests" / "fixtures" / "github_snapshots"
    out = Path(__file__).resolve().parent / "_bench_bundle"
    spec = SnapshotExtractor().extract(snapshots / "fix-percentile-boundary")
    task = scaffold(spec)
    write_bundle(task, out)
    harness = out / "harness" / "test_verification.py"

    def run_state(state: str, broken: bool) -> None:
        cmd = [sys.executable, str(harness)]
        if broken:
            cmd.append("--expect-broken")
        subprocess.run(
            cmd, cwd=str(out / state), capture_output=True, text=True, timeout=180,
            check=True,
        )

    broken_cost = median_s(run_state, "broken", True, repeat=3)
    fixed_cost = median_s(run_state, "solution", False, repeat=3)
    return {
        "broken_state_verify_s": broken_cost,
        "fixed_state_verify_s": fixed_cost,
    }


def main() -> None:
    print(json.dumps({"scaffold_throughput": bench_scaffold_throughput()}, indent=2))
    print(json.dumps({"diff_engine": bench_diff_engine()}, indent=2))
    print(json.dumps({"harness_verification": bench_harness_verification()}, indent=2))


if __name__ == "__main__":
    main()
