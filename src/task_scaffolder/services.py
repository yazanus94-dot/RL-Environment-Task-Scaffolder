"""Repository extraction: turning real-world PRs/issues into TaskSpecs.

Two sources are supported:

* :class:`SnapshotExtractor` -- offline-first. Reads a local snapshot
  directory (recorded GitHub state: files, issue text, solution diff).
  This is the default and the only source used by tests/CI, guaranteeing
  hermetic, reproducible scaffolding.
* :class:`GitHubExtractor` -- live client over the GitHub REST API.
  Disabled by default; requires a token and network. It exists to show
  the production wiring, but the deterministic pipeline never depends on
  it.

Both sources produce identical :class:`TaskSpec` objects for identical
inputs -- the extraction layer is a pure adapter.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from task_scaffolder.core import TaskSpec


class ExtractionError(Exception):
    """Raised when a snapshot or API response cannot be turned into a task."""


def _read_text(path: Path) -> str:
    # utf-8-sig tolerates editor/OS BOMs without corrupting content.
    return path.read_text(encoding="utf-8-sig")


class SnapshotExtractor:
    """Extract TaskSpecs from a recorded snapshot directory.

    Layout::

        snapshots/
          <task_id>/
            snapshot.json     # {"issue": "...", "f2p": [...], "p2p": [...]}
            solution.patch    # unified diff (the PR's fix)
            files/            # repository snapshot *without* the fix
              ...any files...
    """

    def extract(self, snapshot_dir: Path) -> TaskSpec:
        if not snapshot_dir.is_dir():
            raise ExtractionError(f"snapshot not found: {snapshot_dir}")
        meta = json.loads(_read_text(snapshot_dir / "snapshot.json"))
        files: dict[str, str] = {}
        files_root = snapshot_dir / "files"
        for path in sorted(files_root.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            rel = path.relative_to(files_root).as_posix()
            files[rel] = _read_text(path)
        diff = _read_text(snapshot_dir / "solution.patch")
        return TaskSpec(
            task_id=snapshot_dir.name,
            base_files=files,
            solution_diff=diff,
            f2p_tests=tuple(meta["f2p_tests"]),
            p2p_tests=tuple(meta.get("p2p_tests", ())),
            issue_text=meta.get("issue", ""),
            metadata={"source": "snapshot", "origin": meta.get("origin", "recorded")},
        )

    def extract_all(self, root: Path) -> Iterator[TaskSpec]:
        for snapshot_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            yield self.extract(snapshot_dir)


class GitHubExtractor:
    """Live extraction from GitHub PRs (requires token + network).

    The scaffolding pipeline never calls this by default. It is provided
    as the production adapter so the same TaskSpec contract covers both
    offline replays and live pulls.
    """

    def __init__(self, token: str, repo: str) -> None:
        self.token = token
        self.repo = repo

    def fetch_pull_request(self, pr_number: int) -> TaskSpec:
        try:
            import requests  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover
            raise ExtractionError("requests not installed") from exc
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }
        base = f"https://api.github.com/repos/{self.repo}"
        pr = requests.get(f"{base}/pulls/{pr_number}", headers=headers, timeout=30)
        pr.raise_for_status()
        diff_response = requests.get(
            f"{base}/pulls/{pr_number}", headers=headers, timeout=30
        )
        diff_response.raise_for_status()
        diff_text = diff_response.text
        files = requests.get(
            f"{base}/pulls/{pr_number}/files", headers=headers, timeout=30
        )
        files.raise_for_status()
        file_payload: list[dict[str, Any]] = files.json()
        tree = {
            item["filename"]: item.get("previous_content", "")
            for item in file_payload
        }
        return TaskSpec(
            task_id=f"pr-{pr_number}",
            base_files=tree,
            solution_diff=diff_text,
            f2p_tests=tuple(),
            p2p_tests=tuple(),
            issue_text=pr.json().get("body", ""),
            metadata={"source": "github", "repo": self.repo},
        )
