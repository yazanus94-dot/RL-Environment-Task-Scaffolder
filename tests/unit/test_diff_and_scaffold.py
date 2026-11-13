"""Unit tests for the diff engine and scaffolder core."""

from __future__ import annotations

import pytest

from task_scaffolder import (
    DiffError,
    InvalidTaskSpec,
    SolutionLeakError,
    TaskSpec,
    apply_patch,
    diff_stats,
    parse_diff,
    scaffold,
    validate_spec,
)

MULTI_HUNK_DIFF = """\
--- a/lib.txt
+++ b/lib.txt
@@ -1,4 +1,4 @@
 alpha
-beta
+beta_prime
 gamma
 delta
@@ -10,3 +10,4 @@
 kappa
-lambda
+lambda_prime
+lambda_extra
 mu
"""


@pytest.fixture(scope="module")
def lib_files() -> dict[str, str]:
    lines = [f"line{i}" for i in range(1, 15)]
    lines[0] = "alpha"
    lines[1] = "beta"
    lines[2] = "gamma"
    lines[3] = "delta"
    lines[9] = "kappa"
    lines[10] = "lambda"
    lines[11] = "mu"
    return {"lib.txt": "\n".join(lines)}


class TestParseDiff:
    def test_hunk_header_counts(self) -> None:
        patches = parse_diff(MULTI_HUNK_DIFF)
        assert len(patches) == 1
        patch = patches[0]
        assert patch.old_path == "lib.txt"
        h1, h2 = patch.hunks
        assert (h1.old_start, h1.old_count) == (1, 4)
        assert (h2.old_start, h2.old_count) == (10, 3)

    def test_line_kinds(self) -> None:
        h1 = parse_diff(MULTI_HUNK_DIFF)[0].hunks[0]
        kinds = [hl.kind for hl in h1.lines]
        assert kinds == [" ", "-", "+", " ", " "]

    def test_no_patch_raises(self) -> None:
        with pytest.raises(DiffError):
            parse_diff("this is not a diff")


class TestApplyPatch:
    def test_forward_application(self, lib_files: dict[str, str]) -> None:
        out = apply_patch(lib_files, MULTI_HUNK_DIFF)
        content = out["lib.txt"]
        assert "beta_prime" in content
        assert "lambda_extra" in content
        assert "beta\n" not in content.replace("beta_prime", "")
        assert content.count("lambda") == 2

    def test_inverse_application_restores(self, lib_files: dict[str, str]) -> None:
        fixed = apply_patch(lib_files, MULTI_HUNK_DIFF, reverse=False)
        restored = apply_patch(fixed, MULTI_HUNK_DIFF, reverse=True)
        assert restored == lib_files

    def test_reapplication_is_rejected_like_git(self, lib_files: dict[str, str]) -> None:
        """Re-applying the same patch to the fixed tree must fail loudly
        (content verification), never silently duplicate lines."""
        once = apply_patch(lib_files, MULTI_HUNK_DIFF)
        with pytest.raises(DiffError):
            apply_patch(once, MULTI_HUNK_DIFF)

    def test_missing_target_raises(self) -> None:
        with pytest.raises(DiffError):
            apply_patch({"other.txt": "x"}, MULTI_HUNK_DIFF)


class TestDiffStats:
    def test_stats(self) -> None:
        stats = diff_stats(MULTI_HUNK_DIFF)
        assert stats["files"] == ["lib.txt"]
        assert stats["additions"] == 3
        assert stats["deletions"] == 2
        assert stats["hunks"] == 2


class TestValidateSpec:
    def _spec(self, **overrides) -> TaskSpec:
        base = dict(
            task_id="t1",
            base_files={"m.py": "x = 1\n"},
            solution_diff=(
                "--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
            ),
            f2p_tests=("tests/test_m.py::test_x",),
            p2p_tests=(),
            issue_text="x should be 2",
        )
        base.update(overrides)
        return TaskSpec(**base)

    def test_valid_spec_passes(self) -> None:
        validate_spec(self._spec())

    def test_unknown_file_rejected(self) -> None:
        with pytest.raises(InvalidTaskSpec):
            validate_spec(self._spec(task_id=""))
        with pytest.raises(InvalidTaskSpec):
            validate_spec(self._spec(solution_diff="--- a/ghost.py\n+++ b/ghost.py\n@@ -1 +1 @@\n-a\n+b\n"))

    def test_no_f2p_rejected(self) -> None:
        with pytest.raises(InvalidTaskSpec):
            validate_spec(self._spec(f2p_tests=()))

    def test_f2p_p2p_overlap_rejected(self) -> None:
        with pytest.raises(InvalidTaskSpec):
            validate_spec(
                self._spec(
                    f2p_tests=("t1",), p2p_tests=("t1",),
                )
            )

    def test_noop_diff_rejected(self) -> None:
        with pytest.raises(InvalidTaskSpec):
            scaffold(self._spec(solution_diff="--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n x = 1\n"))

    def test_solution_leak_rejected(self) -> None:
        with pytest.raises(SolutionLeakError):
            validate_spec(self._spec(issue_text="the fix is simply: x = 2"))


class TestScaffold:
    def test_bundle_shape(self, sample_snapshot) -> None:
        from task_scaffolder import SnapshotExtractor

        task = scaffold(SnapshotExtractor().extract(sample_snapshot))
        assert set(task.broken_files) == set(task.fixed_files) - set()
        assert "shape_stats/core.py" in task.fixed_files
        assert "harness/test_verification.py" in task.harness_files
        assert task.manifest["task_id"] == "fix-percentile-boundary"

    def test_broken_and_fixed_differ(self, sample_snapshot) -> None:
        from task_scaffolder import SnapshotExtractor

        task = scaffold(SnapshotExtractor().extract(sample_snapshot))
        assert task.broken_files["shape_stats/core.py"] != task.fixed_files["shape_stats/core.py"]

    def test_manifest_is_deterministic(self, sample_snapshot) -> None:
        import json

        from task_scaffolder import SnapshotExtractor

        spec = SnapshotExtractor().extract(sample_snapshot)
        t1, t2 = scaffold(spec), scaffold(spec)
        assert json.dumps(t1.manifest, sort_keys=True) == json.dumps(t2.manifest, sort_keys=True)
