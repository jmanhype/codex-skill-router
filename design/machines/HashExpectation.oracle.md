# Generated transition oracle: `hashExpectation`

Generated from `HashExpectation.machine.json` by `machinery oracle`. DO NOT EDIT BY HAND.
<!-- machinery-version: v0.3.11 -->
Single source of truth for the hard-TDD transition tests: one transition row is one
test case. Key tests on the STABLE id, not the row number; row numbers renumber when
the design changes, stable ids do not.

## State entry / exit actions

| state | kind | entry | exit |
|---|---|---|---|
| Proposed | atomic | - | - |
| Verified | final | - | - |
| Mismatched | final | - | - |

## Transitions

| test id | stable id | source | trigger | guard | target | actions |
|---|---|---|---|---|---|---|
| T-HASH-01 | HASH-f9bb6c | Proposed | on:verify | - | Verified | bindMatchingObservedHash |
| T-HASH-02 | HASH-08bd15 | Proposed | on:mismatch | - | Mismatched | bindMismatchedObservedHash |

Total transitions (test cases): 2
