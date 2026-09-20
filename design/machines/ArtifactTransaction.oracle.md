# Generated transition oracle: `artifactTransaction`

Generated from `ArtifactTransaction.machine.json` by `machinery oracle`. DO NOT EDIT BY HAND.
<!-- machinery-version: v0.3.11 -->
Single source of truth for the hard-TDD transition tests: one transition row is one
test case. Key tests on the STABLE id, not the row number; row numbers renumber when
the design changes, stable ids do not.

## State entry / exit actions

| state | kind | entry | exit |
|---|---|---|---|
| Proposed | atomic | - | - |
| Staged | atomic | - | - |
| Leased | atomic | - | - |
| Committing | atomic | - | - |
| RollingBack | atomic | - | - |
| Recovering | atomic | - | - |
| Committed | final | - | - |
| RolledBack | final | - | - |
| Rejected | final | - | - |
| Recovered | final | - | - |

## Transitions

| test id | stable id | source | trigger | guard | target | actions |
|---|---|---|---|---|---|---|
| T-TXN-01 | TXN-0ce397 | Proposed | on:stage | - | Staged | sealAndVerifyAllSources |
| T-TXN-02 | TXN-78feea | Proposed | on:reject | - | Rejected | appendRejectionAudit |
| T-TXN-03 | TXN-55eac5 | Staged | on:acquireLease | - | Leased | verifyPreHashesAndAcquireLease |
| T-TXN-04 | TXN-07ee49 | Staged | on:leaseDenied | - | Rejected | recordLeaseContention |
| T-TXN-05 | TXN-3958f3 | Staged | on:reject | - | Rejected | appendRejectionAudit |
| T-TXN-06 | TXN-f69729 | Leased | on:commit | - | Committing | capturePreStateAndPrepareAtomicReplacements |
| T-TXN-07 | TXN-92359e | Leased | on:staleHash | - | Rejected | releaseLeaseAndRecordStaleHash |
| T-TXN-08 | TXN-896a3d | Leased | on:crash | - | Recovering | markLeaseOrphaned |
| T-TXN-09 | TXN-fe36a0 | Committing | on:commitAndAuditSucceeded | - | Committed | verifyPostHashesAppendAuditAndReleaseLease |
| T-TXN-10 | TXN-f9d923 | Committing | on:commitFailed | - | RollingBack | restoreCapturedPreState |
| T-TXN-11 | TXN-c06d44 | Committing | on:auditFailed | - | RollingBack | restoreCapturedPreState |
| T-TXN-12 | TXN-d8cb41 | Committing | on:crash | - | Recovering | markLeaseOrphaned |
| T-TXN-13 | TXN-5fd1c7 | RollingBack | on:rollbackSucceeded | - | RolledBack | appendRollbackAuditAndReleaseLease |
| T-TXN-14 | TXN-bbca31 | RollingBack | on:rollbackFailed | - | Recovering | retainPreStateAndMarkOperatorRecoveryRequired |
| T-TXN-15 | TXN-305eaa | Recovering | on:recoverySucceeded | - | Recovered | verifyPreStateAppendRecoveryAuditAndReleaseLease |
| T-TXN-16 | TXN-c5c4ad | Recovering | on:reject | - | Rejected | appendUnsafeRecoveryRejection |

Total transitions (test cases): 16
