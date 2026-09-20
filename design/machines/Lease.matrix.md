# Lease named-unit contract

| name | kind | signature | contract (pre / post) | maps to | test type | fixture |
|---|---|---|---|---|---|---|
| `bindExclusiveOwnerAndExpiry` | action | `(ctx, evt) -> ctx` | atomically binds one owner token and explicit expiry | invariant `lease-exclusive` | concurrency | two acquisition calls |
| `clearOwnerToken` | action | `(ctx, evt) -> ctx` | clears owner after terminal transaction state | invariants `lease-exclusive`, `audit-complete` | integration | clean success/rejection |
| `recordOrphanExpiry` | action | `(ctx, evt) -> ctx` | records abrupt owner loss and expiry without allowing commit | invariant `orphan-recovery-bounded` | integration | crashed owner |
| `auditBoundedRecoveryAndClearOwner` | action | `(ctx, evt) -> ctx` | permits recovery only after expiry and appends evidence | invariants `orphan-recovery-bounded`, `audit-complete` | integration | expired lease |
