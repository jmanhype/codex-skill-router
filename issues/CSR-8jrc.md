---
id: CSR-8jrc
title: "E2e: govern Skill Router through its own Paivot backlog"
status: in_progress
priority: 0
type: task
parent: CSR-knpb
created_at: 2026-09-20T17:02:44Z
created_by: speed
updated_at: 2026-09-20T17:06:20Z
content_hash: "sha256:e6bdd556fe15d4e9076f8eff4acff0f9f4dfc1942b11f2936b8eeb4dc749ef6f"
labels: [e2e, capstone, walking-skeleton, delivered]
assignee: dev-CSR-8jrc
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
## PM Decision
ACCEPTED [2026-09-20]: Independently reviewed the 6-file/124-line governance-only diff, reran the 31-test portable suite, whitespace check, scoped verifier, nd root/sync, doctor, and required PR check review. All eight AC are covered by concrete local and GitHub evidence; no router behavior changed.

## nd_contract
status: accepted

### evidence
- Portable suite: 31/31 passed.
- pvg verify: 1 file scanned, 0 issues.
- pvg doctor: all checks passed.
- PR CI test check: success.
- Story commit: 01fec23b70120ac09a2ed80ec9e17994643e8c51.
- Backlog head before acceptance: 7b5a822e481daee5f7aaa243a60b6b285e8d766e.

### proof
- [x] AC-by-AC independently verified from code, tests, Git, nd, and GitHub PR state.

## nd_contract
status: delivered

### evidence
- Transitioned via pvg story deliver on 2026-09-20.

### proof
- [ ] Developer evidence block must remain authoritative above this contract.


## Implementation Evidence

Commands run:

```bash
/usr/bin/python3 -m unittest discover -s . -p 'test_*.py' -q
git diff --check main..HEAD
pvg verify test_governance.py README.md .paivot/config.yaml .vault/.nd-shared.yaml .vault/.gitignore --format=text
pvg nd root
pvg nd sync --status
pvg doctor
gh pr view 1 --repo jmanhype/codex-skill-router --json state,mergeStateStatus,statusCheckRollup,url
```

### CI/Test Results

```text
portable unittest suite: 31 passed, 0 failed, 0 skipped
git diff --check: PASS
pvg verify: PASSED, 1 file scanned, 0 issues
pvg nd root: repository-local .git/paivot/nd-vault
pvg nd sync --status: vault in sync; remote 0 ahead, 0 behind
pvg doctor: all checks passed
GitHub PR test check: SUCCESS
GitHub PR merge state: CLEAN
story diff: 6 files, 124 insertions
```

### AC Verification

| AC | Result | Evidence |
|---|---|---|
| 1. Repository-local live nd vault | PASS | `pvg nd root` resolves to this checkout's `.git/paivot/nd-vault`. |
| 2. Local nd/vlt providers, no mirrors | PASS | `test_repository_local_paivot_adapters_are_configured` checks active config. |
| 3. Git-common-dir mapping | PASS | `test_nd_uses_git_common_dir_vault` and `.vault/.nd-shared.yaml`. |
| 4. Runtime state ignored | PASS | `test_live_vault_runtime_state_is_not_tracked`; no `issues/` directory committed. |
| 5. Migration documented | PASS | README documents standalone ownership and immutable Wangp history. |
| 6. Regression tests in portable suite | PASS | GovernanceTests run with the existing unittest discovery command. |
| 7. Backlog synced | PASS | `pvg nd sync --status` reports 0 ahead/0 behind. |
| 8. Router behavior unchanged | PASS | Only governance/docs/tests changed; all 31 tests pass and required PR CI is green. |

Summary: established standalone repository-local Paivot governance for Codex Skill Router while preserving router behavior and Wangp's immutable historical stories.

Commit SHA: 01fec23b70120ac09a2ed80ec9e17994643e8c51

Pushed nd/backlog head: c9981dca9ef17321072d5456d7e86111382c9ecb

## nd_contract
status: delivered

### evidence
- Portable suite: 31/31 passed.
- Required GitHub PR test check: success.
- pvg doctor: all checks passed.
- Story commit: `01fec23b70120ac09a2ed80ec9e17994643e8c51`.
- Backlog head: `c9981dca9ef17321072d5456d7e86111382c9ecb`.

### proof
- [x] AC #1: Repository-local nd vault resolves inside this Git repository.
- [x] AC #2: Local nd/vlt providers configured without mirrors.
- [x] AC #3: Git-common-dir shared-vault mapping configured.
- [x] AC #4: Runtime vault state ignored and absent from Git.
- [x] AC #5: Standalone migration documented.
- [x] AC #6: Governance tests integrated into portable suite.
- [x] AC #7: nd backlog synced with remote.
- [x] AC #8: Router behavior unchanged and CI green.

## History
- 2026-09-20T17:02:45Z status: open -> in_progress
- 2026-09-20T17:02:45Z claimed by dev-CSR-8jrc
- 2026-09-20T17:06:01Z status: in_progress -> in_progress

## Links
- Parent: [[CSR-knpb]]

## Comments
