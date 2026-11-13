# Security Considerations

## Trust boundaries

1. **Snapshots are untrusted input.** A malicious snapshot could attempt
   to smuggle content into bundles. Mitigations:
   - `validate_spec` rejects diffs touching unknown files and unparseable
     payloads before any file is written.
   - Bundle content is *derived* (broken/fixed states are pure functions
     of snapshot files + diff), never executed at scaffold time.
   - File writes are confined to the requested output root; relative
     paths from snapshots are normalized through `pathlib` and cannot
     escape (no absolute paths, no `..` -- enforced by construction since
     paths come from `relative_to(files_root)`).
2. **The generated harness executes tests via subprocess pytest.** It
   only ever runs test ids listed in the (validated) spec, from within
   the bundle workspace. No shell interpolation; arguments are passed as
   a list to `subprocess.run`.
3. **Leak prevention is a security property.** `SolutionLeakError`
   guarantees the agent-facing issue text does not contain the fix;
   `solution/` is physically separate from `broken/` in the bundle.

## Injection surface

- No eval/exec/dynamic-import anywhere in the package (ruff `B`/`S` rule
  classes enabled; CI enforces).
- The live `GitHubExtractor` is disabled by default; when enabled it
  requires an explicit token parameter (never read from the environment
  implicitly) and uses TLS via the `requests` stack. Tokens must not be
  committed; pass them per-session.

## Resource bounds

- Snapshot sizes are bounded by design (recorded trees); the extractor
  walks only `files/` and skips caches (`__pycache__`, `.pyc`).
- Harness subprocesses are capped (`timeout=120` per test id, `timeout=300`
  at the CLI), so a pathological task cannot wedge the verifier.

## Known limitations

- The harness trusts the bundle's `conftest.py` (task content executes
  pytest code by design). Bundles are evaluation artifacts, not
  sandboxed executions; running untrusted agent patches is the
  consumer's responsibility (pair with a container sandbox -- see the
  Deterministic-Code-Verifier-Sandbox project for that layer).
- Manifest hashing proves *what* shipped, not *who* shipped it; sign
  bundles externally if provenance matters.
