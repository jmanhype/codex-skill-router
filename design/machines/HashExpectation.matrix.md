# HashExpectation named-unit contract

| name | kind | signature | contract (pre / post) | maps to | test type | fixture |
|---|---|---|---|---|---|---|
| `bindMatchingObservedHash` | action | `(ctx, evt) -> ctx` | stores exact observed SHA-256 only when equal to expectation | invariants `hash-comparison-explicit`, `stale-hash-rejected` | unit | matching bytes |
| `bindMismatchedObservedHash` | action | `(ctx, evt) -> ctx` | stores differing observed SHA-256 and forces rejection | invariants `stale-hash-rejected`, `guard-fail-closed` | unit | changed bytes |
