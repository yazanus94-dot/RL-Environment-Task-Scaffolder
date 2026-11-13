# Benchmark Results

Measured on the reference machine (Windows 11, Python 3.14,
2026-11-12) via `benchmarks/benchmark.py` -- medians over repeated runs.

## 1. Scaffolding throughput (pure pipeline, no pytest)

| Snapshot size (lines) | Full scaffold time | Throughput |
|---|---|---|
| 100 | 0.066 ms | ~15,000 tasks/s |
| 1,000 | 0.154 ms | ~6,500 tasks/s |
| 5,000 | 0.599 ms | ~1,700 tasks/s |

Scaffolding is effectively free: cost grows linearly with snapshot size
and the pipeline is dominated by file hashing, not diff work.

## 2. Diff engine (10,000-line file, 1-line fix)

| Operation | Median time |
|---|---|
| Parse diff | 6.8 µs |
| Forward apply (broken → fixed) | 0.44 ms |
| Inverse apply (fixed → broken) | 0.46 ms |

Application cost is linear in file length (line-copy dominates); the
content-verification pass that guarantees `git apply`-equivalent safety
is within noise of the naive cost.

## 3. Harness verification (real pytest subprocesses)

| Check | Median time |
|---|---|
| Broken state (2 F2P must fail + 1 P2P must pass) | 2.45 s |
| Fixed state (3 tests must pass) | 2.34 s |

Per-test subprocess cost (~0.8 s) is pytest session startup, not task
logic. For scale-up: a persistent pytest server or in-process execution
would cut this ~10x -- listed as future work since subprocess isolation
is what makes verification tamper-resistant.

## 4. Interpretation

- The expensive part of an evaluation environment is *verification*
  (running the tests), not *construction* (scaffolding). Scaffolding a
  1,000-task batch costs < 0.2 s of pipeline time; verifying each task
  twice (broken + fixed polarity) costs ~5 s of pytest time.
- Diff engine performance is comfortably negligible for realistic
  repository files; a 10k-line file applies in under half a millisecond
  with full content verification enabled.
