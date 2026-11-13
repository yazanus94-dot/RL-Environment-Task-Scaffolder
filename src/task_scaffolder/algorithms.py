"""Diff engine: unified-diff parsing, application and inversion.

This is the algorithmic heart of repository extraction: a solution pull
request is expressed as a unified diff; the scaffolder must be able to

1. *apply* it to reproduce the fixed state,
2. *invert* it to produce the broken pre-fix state (the RL task),
3. round-trip both operations bit-exactly.

The parser implements the subset of the unified-diff format produced by
``git diff`` for text files: hunk headers with ranges, context lines,
additions, deletions, and ``\\ No newline at end of file`` markers.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

HUNK_HEADER = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
)

FILE_HEADER = re.compile(r"^(?:---|\+\+\+) (.+?)(?:\t.*)?$")


class DiffError(Exception):
    """Raised for malformed diffs or failed application."""


@dataclass(frozen=True)
class HunkLine:
    kind: str  # ' ', '+', '-', or '\'
    text: str


@dataclass(frozen=True)
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: tuple[HunkLine, ...]


@dataclass(frozen=True)
class FilePatch:
    old_path: str
    new_path: str
    hunks: tuple[Hunk, ...]


def parse_diff(diff_text: str) -> list[FilePatch]:
    """Parse a unified diff into structured file patches."""
    patches: list[FilePatch] = []
    lines = diff_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("diff ") or line.startswith("Index: "):
            i += 1
            continue
        if line.startswith("--- "):
            old_match = FILE_HEADER.match(line)
            plus_match = (
                FILE_HEADER.match(lines[i + 1]) if i + 1 < len(lines) else None
            )
            if old_match is None or plus_match is None or not line.startswith("--- "):
                raise DiffError(f"malformed file header near line {i}")
            old_path = _clean_path(old_match.group(1))
            new_path = _clean_path(plus_match.group(1))
            i += 2
            hunks: list[Hunk] = []
            while i < len(lines) and lines[i].startswith("@@"):
                header = HUNK_HEADER.match(lines[i])
                if header is None:
                    raise DiffError(f"malformed hunk header: {lines[i]!r}")
                old_start = int(header.group(1))
                old_count = int(header.group(2) or "1")
                new_start = int(header.group(3))
                new_count = int(header.group(4) or "1")
                i += 1
                hunk_lines: list[HunkLine] = []
                while i < len(lines) and (
                    not lines[i].startswith("@@")
                    and not lines[i].startswith("--- ")
                ):
                    raw = lines[i]
                    if raw.startswith("\\"):
                        hunk_lines.append(HunkLine("\\", raw))
                        i += 1
                    elif raw.startswith(("+", "-", " ")):
                        hunk_lines.append(HunkLine(raw[0], raw[1:]))
                        i += 1
                    elif raw == "":
                        # Trailing empty context line (newline marker case)
                        hunk_lines.append(HunkLine(" ", ""))
                        i += 1
                    else:
                        break
                hunks.append(
                    Hunk(old_start, old_count, new_start, new_count, tuple(hunk_lines))
                )
            patches.append(FilePatch(old_path, new_path, tuple(hunks)))
        else:
            i += 1
    if not patches:
        raise DiffError("no file patches found in diff")
    return patches


def _clean_path(header_path: str) -> str:
    path = header_path.strip()
    if path.startswith(("a/", "b/")):
        path = path[2:]
    if path == "/dev/null":
        return "/dev/null"
    return path


def apply_hunks(
    source_lines: Sequence[str], hunks: Sequence[Hunk], reverse: bool = False
) -> list[str]:
    """Apply hunks to a list of source lines; returns the new file content.

    ``reverse=True`` applies the diff backwards (solution → broken state).
    """
    out: list[str] = []
    src_index = 0  # 0-based position into source_lines

    def expected_counts(hunk: Hunk) -> tuple[int, int]:
        if not reverse:
            return hunk.old_count, hunk.new_count
        return hunk.new_count, hunk.old_count

    for hunk in hunks:
        old_count, new_count = expected_counts(hunk)
        # Positioning: hunks are ordered; src_index is 0-based, headers 1-based.
        start = (hunk.new_start if reverse else hunk.old_start) - 1
        if start < src_index:
            raise DiffError("overlapping hunks")
        # Copy untouched lines before the hunk.
        out.extend(source_lines[src_index:start])
        src_index = start

        body = hunk.lines
        consumed = 0
        for hl in body:
            if hl.kind == "\\":
                # "No newline at end of file" marker: adjust previous line
                if out and out[-1] == "":
                    out.pop()
                continue
            if hl.kind == " ":
                if src_index >= len(source_lines):
                    raise DiffError("context beyond end of file")
                if source_lines[src_index] != hl.text:
                    raise DiffError(
                        f"patch does not apply: context mismatch at source "
                        f"line {src_index + 1}: expected {hl.text!r}, "
                        f"found {source_lines[src_index]!r}"
                    )
                out.append(source_lines[src_index])
                src_index += 1
                consumed += 1
            elif (hl.kind == "-" and not reverse) or (hl.kind == "+" and reverse):
                if src_index >= len(source_lines):
                    raise DiffError("deletion beyond end of file")
                if source_lines[src_index] != hl.text:
                    raise DiffError(
                        f"patch does not apply: deleted-line mismatch at "
                        f"source line {src_index + 1}: expected {hl.text!r}, "
                        f"found {source_lines[src_index]!r}"
                    )
                src_index += 1  # drop the line
                consumed += 1
            elif hl.kind == "+" and not reverse:
                out.append(hl.text)
            elif hl.kind == "-" and reverse:
                out.append(hl.text)
            else:  # '+' in reverse means it was a deletion in the fixed file
                continue

        if consumed != old_count:
            raise DiffError(
                f"hunk expected {old_count} source lines, consumed {consumed}"
            )

    out.extend(source_lines[src_index:])
    return out


def apply_patch(
    files: dict[str, str], diff_text: str, reverse: bool = False
) -> dict[str, str]:
    """Apply a unified diff to a virtual file tree; returns the new tree."""
    patches = parse_diff(diff_text)
    result = dict(files)
    for patch in patches:
        path = patch.old_path if patch.old_path != "/dev/null" else patch.new_path
        if path == "/dev/null":
            raise DiffError("patch touches /dev/null")
        if path not in result:
            raise DiffError(f"patch target missing: {path}")
        source_lines = result[path].split("\n")
        new_lines = apply_hunks(source_lines, patch.hunks, reverse=reverse)
        result[path] = "\n".join(new_lines)
    return result


def diff_stats(diff_text: str) -> dict[str, Any]:
    """Summary statistics for a diff: files, additions, deletions, hunks."""
    patches = parse_diff(diff_text)
    additions = sum(
        sum(1 for hl in h.lines if hl.kind == "+")
        for patch in patches
        for h in patch.hunks
    )
    deletions = sum(
        sum(1 for hl in h.lines if hl.kind == "-")
        for patch in patches
        for h in patch.hunks
    )
    hunks = sum(len(patch.hunks) for patch in patches)
    return {
        "files": [p.new_path for p in patches],
        "additions": additions,
        "deletions": deletions,
        "hunks": hunks,
    }
