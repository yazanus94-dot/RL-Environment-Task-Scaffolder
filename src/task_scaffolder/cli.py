"""CLI: scaffold task bundles from snapshots and verify their polarity.

Usage::

    python -m task_scaffolder.cli scaffold \
        --snapshot-dir tests/fixtures/github_snapshots --out bundles/

    python -m task_scaffolder.cli verify --bundle bundles/<task_id> \
        --state broken    # expects F2P fail, P2P pass
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from task_scaffolder import SnapshotExtractor, scaffold, write_bundle


def cmd_scaffold(args: argparse.Namespace) -> int:
    extractor = SnapshotExtractor()
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    count = 0
    for spec in extractor.extract_all(Path(args.snapshot_dir)):
        task = scaffold(spec)
        target = out_root / task.manifest["task_id"]
        write_bundle(task, target)
        stats = task.manifest["diff_stats"]
        print(
            f"scaffolded {task.manifest['task_id']}: "
            f"{stats['files']} file(s) touched, +{stats['additions']}/-{stats['deletions']}, "
            f"F2P={len(task.manifest['f2p_tests'])} P2P={len(task.manifest['p2p_tests'])}"
        )
        count += 1
    print(f"total: {count} task bundle(s) written to {out_root}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    harness = Path(args.bundle) / "harness" / "test_verification.py"
    state_dir = Path(args.bundle) / args.state
    expect_broken = args.state == "broken"
    cmd = [sys.executable, str(harness)]
    if expect_broken:
        cmd.append("--expect-broken")
    proc = subprocess.run(
        cmd, cwd=str(state_dir), capture_output=True, text=True, timeout=300
    )
    report_path = state_dir / "verification_report.json"
    if report_path.is_file():
        print(json.dumps(json.loads(report_path.read_text(encoding="utf-8")), indent=2))
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="task-scaffolder")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scaffold = sub.add_parser("scaffold", help="build task bundles from snapshots")
    p_scaffold.add_argument("--snapshot-dir", required=True)
    p_scaffold.add_argument("--out", default="bundles/")
    p_scaffold.set_defaults(func=cmd_scaffold)

    p_verify = sub.add_parser("verify", help="check a bundle state's F2P/P2P polarity")
    p_verify.add_argument("--bundle", required=True)
    p_verify.add_argument("--state", choices=["broken", "solution"], required=True)
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
