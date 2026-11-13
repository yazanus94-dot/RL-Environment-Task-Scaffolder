# Reproducibility

This document is the contract: scaffolding the same TaskSpec twice, on
two different machines, with two different operating systems, produces
**byte-identical task bundles**.

## What makes it reproducible

1. **Hermetic extraction.** The default source is a recorded snapshot
   directory. No network, no clocks, no locale-dependent formatting
   anywhere in the pipeline.
2. **Deterministic diff application.** The diff engine is a pure
   function `files × diff → files` with content verification; no
   environment data participates.
3. **Sorted, timestamp-free manifests.** `build_manifest` sorts paths
   and emits sha256 digests only. `environment_fingerprint` records
   (but does not influence) the builder's Python/platform.
4. **Order-preserving harness.** Generated files are written from
   f-strings over sorted test-id lists.

## Proof layers

| Layer | Evidence | Where |
|---|---|---|
| Same machine, twice | `test_two_builds_byte_identical` | tests/integration |
| All bundled specs | `test_all_specs_scaffold_successfully` | tests/integration |
| Manifest determinism | `test_manifest_is_deterministic` | tests/unit |
| Different OSes | 3-OS × 2-Python CI matrix + `diff -r` of two scaffold runs | .github/workflows/ci.yml |
| Different containers | `docker compose up verify` end-to-end | ci.yml |

## Verification recipe

```bash
python -m task_scaffolder.cli scaffold \
    --snapshot-dir tests/fixtures/github_snapshots --out /tmp/a
python -m task_scaffolder.cli scaffold \
    --snapshot-dir tests/fixtures/github_snapshots --out /tmp/b
diff -r /tmp/a /tmp/b      # exit 0 == reproducible
```

## Known non-goals

- The *runtime* environment an agent runs in (its Python version,
  installed packages) is outside this contract; bundles declare the
  F2P/P2P contract, and consumers containerize the agent workspace.
- Snapshots recorded from a live repo will differ if the upstream repo
  changes; pin the snapshot revision (done via `origin` metadata).
