"""Auto-generated verification harness for task fix-percentile-boundary.

F2P (fail-to-pass):  tests/test_core.py::test_median, tests/test_core.py::test_max_is_hundred_percentile
P2P  (pass-to-pass): tests/test_core.py::test_min_is_zero_percentile

Run: pytest -v
"""
import json
import subprocess
import sys
from pathlib import Path

F2P = ('tests/test_core.py::test_median', 'tests/test_core.py::test_max_is_hundred_percentile')
P2P = ('tests/test_core.py::test_min_is_zero_percentile',)


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
    report = {"task_id": 'fix-percentile-boundary', "expect_f2p_fail": expect_f2p_fail}
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
