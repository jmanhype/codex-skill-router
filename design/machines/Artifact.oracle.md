# Generated transition oracle: `artifact`

Generated from `Artifact.machine.json` by `machinery oracle`. DO NOT EDIT BY HAND.
<!-- machinery-version: v0.3.11 -->
Single source of truth for the hard-TDD transition tests: one transition row is one
test case. Key tests on the STABLE id, not the row number; row numbers renumber when
the design changes, stable ids do not.

## State entry / exit actions

| state | kind | entry | exit |
|---|---|---|---|
| Selected | atomic | - | - |
| Staged | atomic | - | - |
| Committed | atomic | - | - |
| Reverted | final | - | - |

## Transitions

| test id | stable id | source | trigger | guard | target | actions |
|---|---|---|---|---|---|---|
| T-ARTF-01 | ARTF-166f17 | Selected | on:stage | - | Staged | bindStageIdentity |
| T-ARTF-02 | ARTF-8526af | Staged | on:markCommitted | - | Committed | bindPostHash |
| T-ARTF-03 | ARTF-4519af | Committed | on:markReverted | - | Reverted | bindRestoredPreHash |

Total transitions (test cases): 3
