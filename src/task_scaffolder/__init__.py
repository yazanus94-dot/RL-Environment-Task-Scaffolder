"""task_scaffolder: reproducible coding-challenge environments from real repos."""

from __future__ import annotations

from task_scaffolder.algorithms import (
    DiffError,
    apply_hunks,
    apply_patch,
    diff_stats,
    parse_diff,
)
from task_scaffolder.core import (
    ScaffoldedTask,
    TaskSpec,
    build_manifest,
    environment_fingerprint,
    scaffold,
    validate_spec,
    write_bundle,
)
from task_scaffolder.exceptions import (
    ExtractionError,
    HarnessError,
    InvalidTaskSpec,
    ScaffolderError,
    SolutionLeakError,
)
from task_scaffolder.services import GitHubExtractor, SnapshotExtractor

__version__ = "1.0.0"

__all__ = [
    "TaskSpec",
    "ScaffoldedTask",
    "scaffold",
    "write_bundle",
    "validate_spec",
    "build_manifest",
    "environment_fingerprint",
    "parse_diff",
    "apply_patch",
    "apply_hunks",
    "diff_stats",
    "DiffError",
    "SnapshotExtractor",
    "GitHubExtractor",
    "ScaffolderError",
    "InvalidTaskSpec",
    "SolutionLeakError",
    "HarnessError",
    "ExtractionError",
]
