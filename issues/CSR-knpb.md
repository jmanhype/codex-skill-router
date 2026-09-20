---
id: CSR-knpb
title: "Standalone Paivot governance for Codex Skill Router"
status: open
priority: 0
type: epic
created_at: 2026-09-20T17:02:44Z
created_by: speed
updated_at: 2026-09-20T17:02:44Z
content_hash: "sha256:7fd11852f38d22ab284b2cf9b3564f7de80318032cb6efd7c5f858b5c66bf742"
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


## History


## Links


## Comments
