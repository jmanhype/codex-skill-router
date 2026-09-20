# Generated transition oracle: `auditRecord`

Generated from `AuditRecord.machine.json` by `machinery oracle`. DO NOT EDIT BY HAND.
<!-- machinery-version: v0.3.11 -->
Single source of truth for the hard-TDD transition tests: one transition row is one
test case. Key tests on the STABLE id, not the row number; row numbers renumber when
the design changes, stable ids do not.

## State entry / exit actions

| state | kind | entry | exit |
|---|---|---|---|
| Pending | atomic | - | - |
| Recorded | final | - | - |
| Rejected | final | - | - |

## Transitions

| test id | stable id | source | trigger | guard | target | actions |
|---|---|---|---|---|---|---|
| T-AUDI-01 | AUDI-39c46c | Pending | on:append | - | Recorded | appendCanonicalOutcome |
| T-AUDI-02 | AUDI-da531b | Pending | on:rejectAppend | - | Rejected | forceTransactionRollback |

Total transitions (test cases): 2
