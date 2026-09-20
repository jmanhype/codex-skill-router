---
id: CSR-knpb
title: "Standalone Paivot governance for Codex Skill Router"
status: closed
priority: 0
type: epic
created_at: 2026-09-20T17:02:44Z
created_by: speed
updated_at: 2026-09-20T17:54:56Z
content_hash: "sha256:2828cb70f511f0af4af56588b2f70f9f6e21297454d3722e3fe5fd99c48c3ac4"
closed_at: 2026-09-20T17:54:56Z
close_reason: "Accepted: repository-local nd vault, synced backlog, accepted governance story, 31/31 tests, green CI, and immutable historical boundary are all verified."
---

## Description
## Description
Operate Codex Skill Router as a standalone Paivot-governed repository. Historical Skill Router production work remains immutable history in wangp-dspy; all future Skill Router stories are owned by this repository's repository-local nd vault.

## Epic Outcomes
- A repository-local live nd vault is shared safely across all Skill Router worktrees.
- Story claims are atomic within this repository rather than the wangp-dspy shared queue.
- Governance configuration and migration intent are regression-tested.
- Future Skill Router work has a local source of record.

## OUT OF SCOPE
- Changing router behavior or ranking: this epic only establishes governance.
- Moving or rewriting historical wangp-dspy stories: immutable history remains there.
- External skill execution or automatic installation: remains prohibited.

## Acceptance Criteria
1. A repository-local nd vault is initialized and synced to nd/backlog.
2. A governance story is accepted with tests and CI evidence.
3. Future work can be selected through this repository's local backlog.

## MANDATORY SKILLS
- pvg

## nd_contract
status: new

### evidence
- Operator authorized standalone backlog ownership on 2026-09-20.

### proof
- [ ] Pending governance story acceptance.

## Acceptance Criteria


## Design


## Notes
## PM Decision
ACCEPTED [2026-09-20]: Independently verified standalone governance at main commit 999132219a0e798c0cf64e2c4cf8093f01f3c7b6. Repository-local Git-common-dir vault is active and synced; portable suite passed 31/31; GitHub CI succeeded; accepted child CSR-8jrc records AC-level evidence; historical wangp-dspy linkage is documented as immutable history only.

## History
- 2026-09-20T17:54:56Z status: open -> closed

## Links


## Comments
