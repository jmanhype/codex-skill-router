# ArtifactTransaction Named Unit Contracts

## State and transition units

| name | kind | signature | contract (pre / post) | maps to | test type | fixture |
|---|---|---|---|---|---|---|
| `sealAndVerifyAllSources` | action | `(ctx, evt) -> ctx` | pre: complete source declarations. post: all bytes sealed and digest-verified. | invariants `stage-immutable`, `stage-content-addressed`, `hash-comparison-explicit` | integration | repository-owned source set |
| `appendRejectionAudit` | action | `(ctx, evt) -> ctx` | appends transaction ID, actor, stable rejection code, and all observed hashes without target mutation | invariants `guard-fail-closed`, `audit-complete` | integration | invalid declaration fixture |
| `verifyPreHashesAndAcquireLease` | action | `(ctx, evt) -> ctx` | pre: immutable stages. post: every live pre-hash matches and sole lease is acquired. | invariants `stale-hash-rejected`, `lease-exclusive` | integration | temporary root and pre-hash fixtures |
| `recordLeaseContention` | action | `(ctx, evt) -> ctx` | records winning owner identity and rejects loser; loser stage remains evidence | invariants `lease-exclusive`, `stage-immutable`, `guard-fail-closed` | concurrency | two writer processes |
| `capturePreStateAndPrepareAtomicReplacements` | action | `(ctx, evt) -> ctx` | captures exact target bytes and modes, then prepares complete replacement set | invariants `rollback-prestate-only`, `commit-atomic` | integration | multi-target temporary root |
| `releaseLeaseAndRecordStaleHash` | action | `(ctx, evt) -> ctx` | records expected/observed mismatch and releases lease with no target mutation | invariants `stale-hash-rejected`, `guard-fail-closed`, `audit-complete` | integration | changed live file fixture |
| `markLeaseOrphaned` | action | `(ctx, evt) -> ctx` | records owner/expiry metadata and blocks new commit until bounded recovery | invariants `orphan-recovery-bounded`, `guard-fail-closed` | integration | expired owner fixture |
| `verifyPostHashesAppendAuditAndReleaseLease` | action | `(ctx, evt) -> ctx` | installs complete set atomically, verifies all post-hashes, appends audit, releases lease | invariants `commit-atomic`, `post-hash-bound`, `audit-complete` | integration | successful complete set |
| `restoreCapturedPreState` | action | `(ctx, evt) -> ctx` | restores only this transaction's captured pre-state after commit or audit failure | invariants `rollback-prestate-only`, `guard-fail-closed` | integration | induced replacement failure |
| `appendRollbackAuditAndReleaseLease` | action | `(ctx, evt) -> ctx` | verifies restored hashes, appends rollback evidence, releases lease | invariants `rollback-prestate-only`, `audit-complete` | integration | restored byte-for-byte fixture |
| `retainPreStateAndMarkOperatorRecoveryRequired` | action | `(ctx, evt) -> ctx` | retains pre-state and lease evidence; forbids another blind write | invariants `guard-fail-closed`, `orphan-recovery-bounded` | integration | induced rollback failure |
| `verifyPreStateAppendRecoveryAuditAndReleaseLease` | action | `(ctx, evt) -> ctx` | rehashes current bytes, reconciles captured state, appends recovery evidence, releases lease | invariants `orphan-recovery-bounded`, `stale-hash-rejected`, `audit-complete` | integration | expired lease recovery |
| `appendUnsafeRecoveryRejection` | action | `(ctx, evt) -> ctx` | rejects recovery when owner, expiry, pre-state, or audit evidence is incomplete | invariant `guard-fail-closed` | unit | incomplete recovery fixture |

## Failure catalog

| Failure | Trigger | Required outcome | Named unit |
|---|---|---|---|
| Source unreadable | `STAGE` | `Rejected`, no lease | `appendRejectionAudit` |
| Stage digest mismatch | `STAGE` | `Rejected`, immutable stage retained | `appendRejectionAudit` |
| Existing active lease | `LEASE_DENIED` | Losing writer `Rejected`, winner unchanged | `recordLeaseContention` |
| Live bytes changed | `STALE_HASH` | `Rejected`, target unchanged | `releaseLeaseAndRecordStaleHash` |
| Replacement error | `COMMIT_FAILED` | Complete pre-state rollback | `restoreCapturedPreState` |
| Post-hash mismatch | `COMMIT_FAILED` | Complete pre-state rollback | `restoreCapturedPreState` |
| Audit append error | `AUDIT_FAILED` | Complete pre-state rollback | `restoreCapturedPreState` |
| Rollback error | `ROLLBACK_FAILED` | Operator recovery required; no additional blind write | `retainPreStateAndMarkOperatorRecoveryRequired` |
| Owner crash | `CRASH` | Expired lease recovery and fresh hash verification | `markLeaseOrphaned` |
| Recovery evidence incomplete | `REJECT` | `Rejected`, live target unchanged | `appendUnsafeRecoveryRejection` |

## Transition table

| Source | Event | Target | Guard |
|---|---|---|---|
| Proposed | STAGE | Staged | complete source set and all expected source hashes |
| Proposed | REJECT | Rejected | invalid declaration |
| Staged | ACQUIRE_LEASE | Leased | all stages immutable and root free |
| Staged | LEASE_DENIED | Rejected | another valid owner token exists |
| Staged | REJECT | Rejected | stage validation failed |
| Leased | COMMIT | Committing | every live pre-hash matches |
| Leased | STALE_HASH | Rejected | any observed pre-hash differs |
| Leased | CRASH | Recovering | lease owner disappeared before terminal state |
| Committing | COMMIT_AND_AUDIT_SUCCEEDED | Committed | all replacements and post-hashes and audit append succeeded |
| Committing | COMMIT_FAILED | RollingBack | replacement or post-hash failed |
| Committing | AUDIT_FAILED | RollingBack | terminal audit append failed |
| Committing | CRASH | Recovering | owner disappeared during mutation |
| RollingBack | ROLLBACK_SUCCEEDED | RolledBack | every restored hash matches captured pre-state |
| RollingBack | ROLLBACK_FAILED | Recovering | restoration could not be completed |
| Recovering | RECOVERY_SUCCEEDED | Recovered | bounded expiry/current hashes/audit evidence all reconcile |
| Recovering | REJECT | Rejected | recovery evidence incomplete |
