"""Integration tests: full pipeline from snapshot to verified bundle.

The verification harness runs real pytest sessions against the broken and
fixed states; the F2P/P2P polarity must hold in both directions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from task_scaffolder import SnapshotExtractor, scaffold, write_bundle


@pytest.fixture(scope="module")
def bundled_task(sample_snapshot, tmp_path_factory) -> tuple[object, Path]:
    spec = SnapshotExtractor().extract(sample_snapshot)
    task = scaffold(spec)
    root = tmp_path_factory.mktemp("bundle")
    write_bundle(task, root)
    return task, root


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, timeout=180
    )


class TestBundleOnDisk:
    def test_layout(self, bundled_task) -> None:
        _, root = bundled_task
        for sub in ("broken", "solution", "harness"):
            assert (root / sub).is_dir()
        assert (root / "manifest.json").is_file()

    def test_manifest_content(self, bundled_task) -> None:
        _, root = bundled_task
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["task_id"] == "fix-percentile-boundary"
        assert len(manifest["broken"]["files"]) == len(manifest["fixed"]["files"])
        broken_hashes = manifest["broken"]["files"]
        fixed_hashes = manifest["fixed"]["files"]
        assert broken_hashes != fixed_hashes
        assert broken_hashes["conftest.py"] == fixed_hashes["conftest.py"]


class TestTestDrivenPolarity:
    """The heart of the harness contract:

    - broken state: F2P tests FAIL, P2P tests PASS
    - fixed state:  F2P tests PASS, P2P tests PASS
    """

    def _polarity(self, workspace: Path, expect_f2p_fail: bool) -> dict:
        harness = workspace.parent / "harness" / "test_verification.py"
        proc = _run(
            [
                sys.executable,
                str(harness),
                "--expect-broken" if expect_f2p_fail else "--expect-fixed",
            ],
            workspace,
        )
        report_path = workspace / "verification_report.json"
        assert report_path.is_file(), proc.stdout + proc.stderr
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["ok"], report
        return report

    def test_broken_state_fails_f2p_and_passes_p2p(self, bundled_task) -> None:
        _, root = bundled_task
        report = self._polarity(root / "broken", expect_f2p_fail=True)
        assert report["tests/test_core.py::test_median"] == "fail"
        assert report["tests/test_core.py::test_max_is_hundred_percentile"] == "fail"
        assert report["tests/test_core.py::test_min_is_zero_percentile"] == "pass"

    def test_fixed_state_passes_everything(self, bundled_task) -> None:
        _, root = bundled_task
        report = self._polarity(root / "solution", expect_f2p_fail=False)
        for key in ("tests/test_core.py::test_median",
                    "tests/test_core.py::test_max_is_hundred_percentile",
                    "tests/test_core.py::test_min_is_zero_percentile"):
            assert report[key] == "pass"


class TestReproducibility:
    def test_two_builds_byte_identical(self, sample_snapshot, tmp_path) -> None:
        spec = SnapshotExtractor().extract(sample_snapshot)
        root_a, root_b = tmp_path / "a", tmp_path / "b"
        write_bundle(scaffold(spec), root_a)
        write_bundle(scaffold(spec), root_b)
        manifest_a = (root_a / "manifest.json").read_text(encoding="utf-8")
        manifest_b = (root_b / "manifest.json").read_text(encoding="utf-8")
        assert manifest_a == manifest_b

    def test_all_specs_scaffold_successfully(self, all_specs) -> None:
        assert len(all_specs) >= 2
        for spec in all_specs:
            task = scaffold(spec)
            assert task.manifest["broken"] != task.manifest["fixed"]
