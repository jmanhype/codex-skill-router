# StagedArtifact named-unit contract

| name | kind | signature | contract (pre / post) | maps to | test type | fixture |
|---|---|---|---|---|---|---|
| `bindInstalledHash` | action | `(ctx, evt) -> ctx` | marks sealed bytes committed without changing stage bytes | invariants `stage-immutable`, `post-hash-bound` | integration | installed temporary target |
| `preserveRejectedBytes` | action | `(ctx, evt) -> ctx` | preserves losing/mismatched bytes as immutable evidence | invariants `stage-immutable`, `guard-fail-closed` | integration | hash mismatch |
| `preserveRetiredBytes` | action | `(ctx, evt) -> ctx` | retires uninstalled bytes without deletion or mutation | invariant `stage-immutable` | unit | retired stage |
