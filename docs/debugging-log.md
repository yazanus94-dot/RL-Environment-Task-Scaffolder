# Debugging Log

Issues hit while building the scaffolder, each caught by the test suite.

## Issue 1: stale patches silently corrupted files instead of failing

- **Symptom:** the Hypothesis round-trip suite generated a case where a
  patch was applied to a file whose target line had *already changed*
  (same content prefix matched). Instead of erroring, the engine
  duplicated lines: applying the percentile diff to the fixed tree
  produced two `lambda_extra` lines.
- **Root cause:** `apply_hunks` consumed deletion/context lines
  positionally without comparing their text to the diff's expected
  content. Real diffs are position-guided but content-anchored.
- **Debugging approach:** minimized the failing Hypothesis case
  (a 3-line file, two mutations at the same index), then compared the
  behavior with `git apply`, which refuses with "patch does not apply".
- **Fix:** content verification on every consumed line -- deleted and
  context lines must match the file, otherwise `DiffError`.
- **Regression tests:** `test_reapplication_is_rejected_like_git`,
  plus the round-trip property suite that originally caught it.

## Issue 2: BOM broke snapshot loading

- **Symptom:** `json.JSONDecodeError: Unexpected UTF-8 BOM` on
  Windows-authored snapshots.
- **Root cause:** Windows editors (and PowerShell 5.1 `Set-Content`)
  emit UTF-8 with BOM; `Path.read_text(encoding="utf-8")` does not
  strip it, so `json.loads` chokes on the first three bytes.
- **Fix:** snapshot reads use `utf-8-sig`, which tolerates BOM
  presence/absence and never alters non-BOM content.
- **Lesson:** cross-OS tools must accept both encodings at every I/O
  boundary; this is exactly the class of bug the OS matrix CI catches.

## Issue 3: fixture snapshots were collected as tests (and their broken
state "failed" the suite)

- **Symptom:** pytest collected `tests/fixtures/**/tests/test_core.py`
  -- the intentionally-broken task states -- and failed the run.
- **Root cause:** fixture snapshots contain real test files by design
  (they are the F2P/P2P targets); nothing told pytest they are data.
- **Fix:** `collect_ignore_glob = ["fixtures/*"]` in the tests
  conftest; snapshots are inputs, not suite members.

## Issue 4: bundle writer double-nested the harness

- **Symptom:** `bundle/harness/harness/test_verification.py`.
- **Root cause:** harness file keys already include the `harness/`
  prefix, but `write_bundle` prepended it a second time.
- **Fix:** broken/solution trees are written under their subdirectory;
  harness keys are used verbatim.
- **Regression test:** `TestBundleOnDisk::test_layout` pins the layout,
  and the polarity integration tests would fail loudly on any path
  drift since they execute the harness from its absolute location.

## Issue 5: generator closed after reporting a corrupt record

- **Symptom (design review, pre-test):** iterating
  `parse_records(..., on_error=...)` would permanently close the
  generator after the first bad row in strict mode.
- **Fix:** error callbacks are invoked inside the generator body and
  the loop continues; strict mode raises from the same code path.
- **Regression test:** `test_lenient_mode_continues`.
