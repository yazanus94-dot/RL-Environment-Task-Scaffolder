"""Task-spec validation and harness errors."""

from __future__ import annotations


class ScaffolderError(Exception):
    """Base class for scaffolder errors."""


class InvalidTaskSpec(ScaffolderError):
    """A TaskSpec is malformed, inconsistent, or trivial."""


class SolutionLeakError(ScaffolderError):
    """The issue text leaks fixed source code to the agent."""


class HarnessError(ScaffolderError):
    """Harness generation or verification failed."""


class ExtractionError(ScaffolderError):
    """Snapshot or GitHub extraction failed."""
