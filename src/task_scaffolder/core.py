"""Core scaffolding: TaskSpec, manifests, and the scaffolding pipeline.

A *task bundle* is a fully reproducible coding-challenge environment:

- ``broken/``  -- the pre-fix repository state (the RL agent's workspace)
- ``solution/``-- the fixed state (never shown to the agent)
- ``harness/`` -- pytest suite with F2P (fail-to-pass) and P2P
                 (pass-to-pass) test ids
- ``manifest.json`` -- sha256 of every file + environment fingerprint

Reproducibility contract: scaffolding the same TaskSpec twice on any
machine produces byte-identical ``manifest.json`` content (file order
sorted, timestamps absent).
"""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from task_scaffolder.algorithms import apply_patch, diff_stats, parse_diff
from task_scaffolder.exceptions import (
    HarnessError,
    InvalidTaskSpec,
    SolutionLeakError,
)


@dataclass(frozen=True)
class TaskSpec:
    """Declarative description of one coding-challenge task."""

    task_id: str
    base_files: dict[str, str]          # repository snapshot WITHOUT the fix
    solution_diff: str                  # unified diff turning base -> fixed
    f2p_tests: tuple[str, ...]          # must FAIL before, PASS after
    p2p_tests: tuple[str, ...]          # must PASS before AND after
    issue_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScaffoldedTask:
    """The emitted task bundle (in-memory form)."""

    spec: TaskSpec
    broken_files: dict[str, str]
    fixed_files: dict[str, str]
    harness_files: dict[str, str]
    manifest: dict[str, Any]


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_manifest(files: dict[str, str]) -> dict[str, Any]:
    """Deterministic manifest: sorted keys, no timestamps, no locale data."""
    return {
        "algorithm": "sha256",
        "files": {path: sha256(content) for path, content in sorted(files.items())},
        "total_files": len(files),
    }


def environment_fingerprint() -> dict[str, Any]:
    """Reproducibility fingerprint of the *scaffolder* environment."""
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(terse=True),
    }


def validate_spec(spec: TaskSpec) -> None:
    """Reject malformed or leaky specs before any file is produced."""
    if not spec.task_id:
        raise InvalidTaskSpec("task_id must be non-empty")
    try:
        patches = parse_diff(spec.solution_diff)
    except Exception as exc:
        raise InvalidTaskSpec(f"solution_diff unparseable: {exc}") from exc
    touched = {p.new_path for p in patches} | {p.old_path for p in patches}
    missing = touched - set(spec.base_files) - {"solution"}
    if missing:
        raise InvalidTaskSpec(f"diff touches unknown files: {sorted(missing)}")
    if not spec.f2p_tests:
        raise InvalidTaskSpec("at least one fail-to-pass test is required")
    overlap = set(spec.f2p_tests) & set(spec.p2p_tests)
    if overlap:
        raise InvalidTaskSpec(f"test ids in both F2P and P2P: {sorted(overlap)}")
    # Leak detection: solution source must not ship inside the issue text.
    for patch in patches:
        for hunk in patch.hunks:
            for hl in hunk.lines:
                if hl.kind == "+" and hl.text.strip() in spec.issue_text:
                    raise SolutionLeakError(
                        f"issue text contains fixed code: {hl.text!r}"
                    )


def generate_harness(spec: TaskSpec) -> dict[str, str]:
    """Produce the pytest harness files for the task bundle."""
    test_targets = sorted(set(spec.f2p_tests) | set(spec.p2p_tests))
    runner = f'''\
"""Auto-generated verification harness for task {spec.task_id}.

F2P (fail-to-pass):  {", ".join(spec.f2p_tests)}
P2P  (pass-to-pass): {", ".join(spec.p2p_tests)}

Run: pytest -v
"""
import json
import subprocess
import sys
from pathlib import Path

F2P = {spec.f2p_tests!r}
P2P = {spec.p2p_tests!r}


def _run(test_id: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", test_id, "-q", "--no-header"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.returncode, proc.stdout + proc.stderr


def verify_state(expect_f2p_fail: bool) -> dict:
    """Check the workspace satisfies the expected F2P/P2P polarity."""
    report = {{"task_id": {spec.task_id!r}, "expect_f2p_fail": expect_f2p_fail}}
    ok = True
    for test_id in F2P:
        code, _ = _run(test_id)
        failed = code != 0
        report[test_id] = "fail" if failed else "pass"
        if failed != expect_f2p_fail:
            ok = False
    for test_id in P2P:
        code, _ = _run(test_id)
        report[test_id] = "pass" if code == 0 else "fail"
        if code != 0:
            ok = False
    report["ok"] = ok
    return report


if __name__ == "__main__":
    expect_fail = "--expect-broken" in sys.argv
    result = verify_state(expect_f2p_fail=expect_fail)
    Path("verification_report.json").write_text(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)
'''
    return {
        "harness/test_verification.py": runner,
        "harness/ISSUE.md": (
            f"# Task {spec.task_id}\n\n{spec.issue_text}\n\n"
            f"## Verification tests\n\n"
            f"- Fail-to-pass: {', '.join(spec.f2p_tests)}\n"
            f"- Pass-to-pass: {', '.join(spec.p2p_tests)}\n"
        ),
    }


def scaffold(spec: TaskSpec) -> ScaffoldedTask:
    """Produce the full task bundle: broken state, fixed state, harness."""
    validate_spec(spec)
    try:
        broken_files = dict(spec.base_files)
        fixed_files = apply_patch(spec.base_files, spec.solution_diff, reverse=False)
    except Exception as exc:
        raise InvalidTaskSpec(f"failed to apply solution diff: {exc}") from exc

    broken_manifest = build_manifest(broken_files)
    fixed_manifest = build_manifest(fixed_files)
    if broken_manifest == fixed_manifest:
        raise InvalidTaskSpec("solution diff changes nothing; task is trivial")

    harness_files = generate_harness(spec)
    manifest = {
        "task_id": spec.task_id,
        "broken": broken_manifest,
        "fixed": fixed_manifest,
        "diff_stats": diff_stats(spec.solution_diff),
        "f2p_tests": list(spec.f2p_tests),
        "p2p_tests": list(spec.p2p_tests),
        "scaffolder_env": environment_fingerprint(),
    }
    return ScaffoldedTask(
        spec=spec,
        broken_files=broken_files,
        fixed_files=fixed_files,
        harness_files=harness_files,
        manifest=manifest,
    )


def write_bundle(task: ScaffoldedTask, root: Path) -> None:
    """Materialize the bundle on disk: broken/, solution/, harness/, manifest."""
    for sub, files in (("broken", task.broken_files), ("solution", task.fixed_files)):
        for rel, content in files.items():
            target = root / sub / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    for rel, content in task.harness_files.items():  # keys already include harness/
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps(task.manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
