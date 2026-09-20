# Generated transition oracle: `lease`

Generated from `Lease.machine.json` by `machinery oracle`. DO NOT EDIT BY HAND.
<!-- machinery-version: v0.3.11 -->
Single source of truth for the hard-TDD transition tests: one transition row is one
test case. Key tests on the STABLE id, not the row number; row numbers renumber when
the design changes, stable ids do not.

## State entry / exit actions

| state | kind | entry | exit |
|---|---|---|---|
| Free | atomic | - | - |
| Acquired | atomic | - | - |
| Orphaned | atomic | - | - |
| Released | final | - | - |

## Transitions

| test id | stable id | source | trigger | guard | target | actions |
|---|---|---|---|---|---|---|
| T-LEAS-01 | LEAS-d276b5 | Free | on:acquire | - | Acquired | bindExclusiveOwnerAndExpiry |
| T-LEAS-02 | LEAS-07f187 | Acquired | on:release | - | Released | clearOwnerToken |
| T-LEAS-03 | LEAS-60ee49 | Acquired | on:markOrphaned | - | Orphaned | recordOrphanExpiry |
| T-LEAS-04 | LEAS-941578 | Orphaned | on:recoverOrphan | - | Released | auditBoundedRecoveryAndClearOwner |

Total transitions (test cases): 4
