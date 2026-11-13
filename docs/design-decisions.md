# Design Decisions

## 1. Offline-first extraction (snapshots) with a live adapter

**Decision:** snapshots are the default and only CI-exercised source;
`GitHubExtractor` exists but is never on the default path.

**Trade-off:** live extraction is fresher but non-deterministic (upstream
repos change, rate limits, network). Recorded snapshots make the
*scaffolding* layer fully reproducible, which is the product. The live
adapter shares the `TaskSpec` contract, so it can be enabled without
touching verified code.

## 2. Solution diff inversion instead of storing the broken state

**Decision:** the snapshot stores the *fixed* files' diff; the broken
state is synthesized by applying it backwards.

**Trade-off:**

| Approach | Authenticity | Storage | Consistency risk |
|---|---|---|---|
| Store broken state directly | lower (hand-edited) | 2x trees | broken/fixed can drift apart |
| **Diff inversion (chosen)** | derived from the real PR | 1 diff | impossible to drift -- fixed is defined by broken+diff |

Inversion also makes the *relationship* between states explicit and
verifiable: `apply(invert(broken)) == fixed` is a property test.

## 3. Content-anchored diff application

**Decision:** every deleted/context line is verified against file
content; mismatch is a hard error.

**Reasoning:** position-only application corrupts files silently (the
bug that motivated this rule). Content verification gives `git apply`'s
refusal semantics and turns stale patches into loud failures -- essential
when the diff is the *definition* of the task.

## 4. F2P/P2P polarity as the correctness contract

**Decision:** a task bundle is valid iff, in the broken state, every F2P
test fails and every P2P test passes; in the fixed state, everything
passes.

**Reasoning:** this is the strongest cheap check that (a) the bug is
real and observable, (b) the fix is complete, and (c) the agent cannot
"solve" the task by breaking unrelated code (P2P pins regressions). The
polarity is re-verified from the generated bundle on every CI run --
the harness is a test artifact, not a promise.

## 5. Leak detection at validation time

**Decision:** reject specs whose issue text quotes fixed source lines.

**Reasoning:** an agent that sees the fix in the issue isn't solving the
task. Checking is one loop over hunk lines; the false-positive cost
(paraphrasing required in issue text) is trivially worth it.

## 6. Manifests as sha256 trees, no timestamps

**Decision:** `manifest.json` = sorted {path: sha256} + diff stats +
scaffolder environment fingerprint.

**Reasoning:** any timestamp or unsorted structure would make the
"byte-identical across builds" contract impossible. The environment
fingerprint is recorded *for diagnosis* but excluded from equality
comparisons by consumers who need OS-agnostic identity.
