# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-11-12

### Added
- Deterministic diff engine: unified-diff parsing, content-anchored
  application, and inverse application (broken state synthesis) with
  `git apply`-equivalent refusal semantics.
- TaskSpec contract with validation: unknown-file rejection, F2P/P2P
  consistency, no-op detection, and issue-text solution-leak detection.
- Snapshot extractor (offline-first, hermetic) plus an optional live
  GitHub REST adapter sharing the same contract.
- Generated test-driven harness with F2P (fail-to-pass) / P2P
  (pass-to-pass) polarity verification via real pytest subprocesses.
- Byte-identical reproducibility: sorted sha256 manifests, cross-OS
  6-cell CI matrix, double-scaffold `diff -r` job.
- Two recorded task snapshots (percentile off-by-one, clamp argument
  order) with proven polarity on both states.
- Property suite: diff round-trips on arbitrary mutation sites,
  order-independent manifests, mutation generators.
- Docker Compose end-to-end service (scaffold + verify both states).
