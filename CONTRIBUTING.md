# Contributing to RL-Environment-Task-Scaffolder

Thank you for considering a contribution. The project's promise is that
every task bundle is reproducible and every polarity claim is verified;
contributions must not weaken either.

## Ground rules

1. **Reproducibility is non-negotiable.** No timestamps, no unsorted
   structures, no locale-dependent output in manifests or generated
   files. `diff -r` of two scaffold runs must stay clean.
2. **Polarity is verified, not promised.** New task snapshots must come
   with F2P and P2P test ids, and the integration suite re-checks both
   states on every run.
3. **Diff semantics stay git-faithful.** Content verification on
   deleted/context lines may not be relaxed; stale patches must fail
   loudly.
4. **Fixtures are data, not tests.** Anything under `tests/fixtures/`
   stays excluded from pytest collection.
5. **Type hints everywhere.** `mypy --strict` must pass.

## Workflow

```bash
git clone https://github.com/<you>/RL-Environment-Task-Scaffolder
cd RL-Environment-Task-Scaffolder
pip install -r requirements.txt
pip install -e .
ruff check .
mypy src
pytest -v
python benchmarks/benchmark.py
```

## Adding a task snapshot

1. Create `tests/fixtures/github_snapshots/<task_id>/` with
   `snapshot.json`, `solution.patch`, and `files/` (pre-fix state).
2. Ensure the F2P tests genuinely fail on `files/` and pass after the
   patch; P2P tests must pass on both states.
3. Run the integration suite -- the harness verifies both polarities
   automatically.

## Commit style

Small, meaningful commits: `feat: clamp argument-order snapshot`,
`fix(diff): verify deleted-line content before consuming`.

## Pull requests

- State whether the PR touches the diff engine, extraction, harness,
  or docs.
- All CI cells (3 OSes × 2 Pythons, reproducibility, docker) green.
