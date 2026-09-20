# Generated transition oracle: `stagedArtifact`

Generated from `StagedArtifact.machine.json` by `machinery oracle`. DO NOT EDIT BY HAND.
<!-- machinery-version: v0.3.11 -->
Single source of truth for the hard-TDD transition tests: one transition row is one
test case. Key tests on the STABLE id, not the row number; row numbers renumber when
the design changes, stable ids do not.

## State entry / exit actions

| state | kind | entry | exit |
|---|---|---|---|
| Sealed | atomic | - | - |
| Rejected | final | - | - |
| Committed | final | - | - |
| Retired | final | - | - |

## Transitions

| test id | stable id | source | trigger | guard | target | actions |
|---|---|---|---|---|---|---|
| T-STAG-01 | STAG-cfb530 | Sealed | on:markCommitted | - | Committed | bindInstalledHash |
| T-STAG-02 | STAG-8af0e4 | Sealed | on:reject | - | Rejected | preserveRejectedBytes |
| T-STAG-03 | STAG-910d99 | Sealed | on:retire | - | Retired | preserveRetiredBytes |

Total transitions (test cases): 3
