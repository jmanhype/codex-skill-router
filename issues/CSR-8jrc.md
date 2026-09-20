---
id: CSR-8jrc
title: "E2e: govern Skill Router through its own Paivot backlog"
status: open
priority: 0
type: task
parent: CSR-knpb
created_at: 2026-09-20T17:02:44Z
created_by: speed
updated_at: 2026-09-20T17:02:44Z
content_hash: "sha256:1d82466542721f2fb1fafe03491a302ed97c5ae50280f5b253b126c165efb638"
labels: [e2e, capstone]
---

## Description
## USER INTENT
The operator needs future Codex Skill Router changes to have their own atomic story queue, evidence flow, and acceptance history inside this repository rather than borrowing Wangp DSPy's backlog.

## Context (Embedded)
This repository currently has green production code and CI but no native Paivot configuration. Historical router production stories live in wangp-dspy because the router affects machine-global Codex artifacts. That history remains immutable. This story establishes repository-local governance only.

## OUT OF SCOPE
- Router ranking or hook behavior changes: unrelated production behavior.
- Migration or deletion of historical wangp-dspy issues: preserve immutable history there.
- External skill pack indexing: later standalone stories.
- Arbitrary skill execution: permanently outside router behavior.

## DIFF BUDGET
- ~5 files, under 200 changed LOC.

## Boundary Map
PRODUCES:
- .paivot/config.yaml -> repository-local nd backlog and vlt notes provider configuration
- .vault/.nd-shared.yaml -> git_common_dir mapping to paivot/nd-vault
- .vault/.gitignore -> runtime-vault exclusions
- test_governance.py -> GovernanceTests proving local adapters, vault mapping, exclusions, and migration documentation
- README.md -> standalone governance and historical-source instructions

CONSUMES:
- (existing): .github/workflows/ci.yml -> python -m unittest discover -s . -p 'test_*.py'

## Acceptance Criteria
1. pvg resolves the live nd vault to this repository's Git-common-dir paivot/nd-vault.
2. .paivot/config.yaml selects repository-local nd and vlt adapters with no mirrors.
3. .vault/.nd-shared.yaml declares mode git_common_dir and path paivot/nd-vault.
4. Live vault runtime files are ignored and no vault issues directory is committed.
5. README documents standalone ownership and identifies wangp-dspy as immutable historical governance.
6. Governance regression tests run in the existing portable unittest suite.
7. pvg nd sync --status reports the vault in sync after the backlog is pushed.
8. Router behavior and portable router tests remain unchanged.

## Testing Requirements
- Unit: test_governance.py must validate provider config, shared-vault mapping, exclusions, and README migration text.
- Integration: MUST be real integration with pvg nd root/sync and Git; no mocks.
- Commands:
  - /usr/bin/python3 -m unittest discover -s . -p 'test_*.py' -q
  - pvg nd root
  - pvg nd sync --status
  - git diff --check

## MANDATORY SKILLS
- pvg

## Delivery Requirements
- Paste exact command output into story notes.
- Include an AC verification table.
- Include the story commit SHA and pushed nd/backlog head.

## nd_contract
status: new

### evidence
- Created for the operator-approved standalone governance goal.

### proof
- [ ] Pending implementation and PM review.

## Acceptance Criteria


## Design


## Notes


## History


## Links
- Parent: [[CSR-knpb]]

## Comments
