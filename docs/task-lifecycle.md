# Task Lifecycle

The complete life of one task, using the bundled fixture
`fix-percentile-boundary` as the running example.

## 1. Capture (snapshot)

A real-world pull request is recorded into a snapshot directory:

```
fix-percentile-boundary/
  snapshot.json     # issue text, F2P ids, P2P ids, provenance
  solution.patch    # the PR's unified diff (what the maintainer merged)
  files/            # repository state WITHOUT the fix (pre-PR)
      conftest.py
      shape_stats/__init__.py
      shape_stats/core.py
      tests/test_core.py
```

Snapshots are the hermetic source of truth: CI, tests, and benchmarks
never touch the network.

## 2. Validate

`validate_spec` rejects, before any output exists:

- unparseable diffs, diffs touching files absent from the snapshot,
- tasks with no F2P tests (nothing can prove the fix matters),
- test ids that appear in both F2P and P2P (contradictory polarity),
- **solution leaks** -- if the issue text quotes fixed source code, the
  agent could pattern-match instead of reasoning; the spec is rejected.

## 3. Invert to the broken state

`solution_diff` is applied **backwards** to the base files. The engine
verifies every deleted/context line against the actual file content
(mismatch ⇒ `DiffError`, the `git apply` contract). For the fixture:

```
broken:  k = len(sorted_values) * p / 100.0     # off-by-one bug
fixed:   k = (len(sorted_values) - 1) * p / 100.0
```

The broken state is what the RL agent receives; the fixed state is
ground truth it never sees.

## 4. Wrap in the test-driven harness

`harness/test_verification.py` is generated with the exact test ids:

| Polarity | Tests | Broken state | Fixed state |
|---|---|---|---|
| F2P (fail-to-pass) | `test_median`, `test_max_is_hundred_percentile` | **must fail** | must pass |
| P2P (pass-to-pass) | `test_min_is_zero_percentile` | must pass | must pass |

The runner executes each id as a real pytest subprocess and writes a
`verification_report.json`. A bundle is valid only if *both* states show
the correct polarity -- proven by `TestTestDrivenPolarity` on every CI
run, not just at generation time.

## 5. Manifest and reproducibility

`manifest.json` holds the sha256 of every file in both states, sorted
key order, no timestamps, plus the scaffolder environment fingerprint.
Consequences:

- two scaffolds on the same machine are byte-identical (proven by
  `test_two_builds_byte_identical`),
- two scaffolds on *different OSes* are byte-identical (proven by the
  6-cell OS×Python CI matrix),
- a consumer can verify any bundle it receives against the manifest.

## 6. Consumption

An agent gets `broken/` + `harness/ISSUE.md` and proposes a patch. The
evaluation applies the patch and runs the harness without
`--expect-broken`: the task is solved iff the report is `ok: true`. The
`solution/` directory stays with the task owner as ground truth.
