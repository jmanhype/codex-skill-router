# Artifact named-unit contract

| name | kind | signature | contract (pre / post) | maps to | test type | fixture |
|---|---|---|---|---|---|---|
| `bindStageIdentity` | action | `(ctx, evt) -> ctx` | binds one immutable stage identity to the selected source/target pair | invariants `artifact-source-pinned`, `stage-content-addressed` | unit | selected source set |
| `bindPostHash` | action | `(ctx, evt) -> ctx` | binds installed bytes only after post-hash verification | invariants `live-artifact-byte-bound`, `post-hash-bound` | integration | installed target |
| `bindRestoredPreHash` | action | `(ctx, evt) -> ctx` | binds the restored pre-state hash after rollback | invariant `rollback-prestate-only` | integration | restored target |
