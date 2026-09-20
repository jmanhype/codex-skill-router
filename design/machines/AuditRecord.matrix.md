# AuditRecord named-unit contract

| name | kind | signature | contract (pre / post) | maps to | test type | fixture |
|---|---|---|---|---|---|---|
| `appendCanonicalOutcome` | action | `(ctx, evt) -> ctx` | appends one canonical terminal outcome with complete hashes | invariants `audit-complete`, `post-hash-bound` | integration | terminal outcome |
| `forceTransactionRollback` | action | `(ctx, evt) -> ctx` | signals rollback when audit bytes cannot be appended | invariants `audit-complete`, `guard-fail-closed` | integration | unwritable audit log |
