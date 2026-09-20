---
id: CSR-97nc
title: "Machinery: design fail-closed global artifact transaction"
status: in_progress
priority: 0
type: task
labels: [machinery, security]
parent: CSR-jg64
created_at: 2026-09-20T19:50:05Z
created_by: speed
updated_at: 2026-09-20T19:51:07Z
content_hash: "sha256:dfc966a86ee149d27492948735e3050a12a762dafebf4f7fc309de18eb2999aa"
blocks: [CSR-ho03]
assignee: dev-CSR-97nc
---

## Description
## USER INTENT
The operator wants the concurrency and failure semantics of the machine-global artifact guard specified by Machinery before production code changes.

## Context (Embedded)
The canonical checkout is Python stdlib-only. The live runtime is `/Users/speed/.codex/skill-router`. Historical WD-m6pq showed that a Paivot story claim does not lock arbitrary machine-global files. The design must model transaction, staged artifact, lease, hash expectation, commit, rollback, and audit outcome as brownfield behavior without deploying the live hook.

## OUT OF SCOPE
- Production implementation in this story.
- Mutating `/Users/speed/.codex/skill-router` or `/Users/speed/.codex/hooks.json`.
- Router ranking or behavior redesign.
- Changing the live hook registration.

## DIFF BUDGET
- Design artifacts only; under 1,200 changed LOC.

## Boundary Map
PRODUCES:
- design/DECISIONS.md -> binding brownfield decisions
- design/STATE.md -> Machinery phase ledger
- design/domain.modelith.yaml and domain.modelith.md -> canonical entities, invariants, actions, and scenarios
- design/workspace.dsl and design/ARCHITECTURE.md -> C4 and Architecture Contract
- design/machines/ArtifactTransaction.machine.json/.matrix.md/.oracle.md -> canonical state machine and transition oracle
- design/BUILD.md -> hard-TDD implementation blueprint

CONSUMES:
- hook.py -> current router runtime entry point
  spec: main() -> int
- MIGRATION.md -> canonical/live runtime boundary
  schema: Markdown migration and live-runtime boundary description
- HASHES.sha256 -> accepted source hash precedent
  schema: SHA256 manifest over accepted canonical source files

## Story Contract
The user can inspect a Machinery design whose oracle proves every legal and illegal global-artifact transaction transition before implementation.

1. Machinery Phase 0 classifies this as a Python brownfield guard and records that live deployment is out of scope.
2. The domain model identifies Artifact, StagedArtifact, HashExpectation, Lease, Transaction, and AuditRecord with owners, attributes, relationships, actions, and lifecycle statuses.
3. Invariants cover single-active-lease, expected-hash match, immutable staged bytes, no partial commit, rollback preservation, audit completeness, fail-closed errors, and no arbitrary skill execution.
4. Scenarios cover uncontested commit, stale hash, already leased, stage mismatch, commit failure, rollback, crash recovery, and audit inspection.
5. C4 and the Architecture Contract identify the guard, canonical source, staged store, lease store, live global filesystem, audit log, and CLI/test boundaries with failure postures.
6. The ArtifactTransaction machine and generated oracle enumerate every legal transition and failure path with stable IDs.
7. BUILD.md derives a hard-TDD implementation plan whose tests cite committed oracle stable IDs.
8. `modelith lint`, applicable Machinery phase gates, and Paivot backlog lint pass before delivery.

## Testing Requirements
- `modelith lint design/domain.modelith.yaml`
- `machinery check design --gate gc`
- `machinery check design --gate g2`
- `machinery check design --gate g3,gx,gb`
- `pvg lint --backlog`

## MANDATORY SKILLS
- pvg
- machinery
- domain_model
- c4

## nd_contract
status: new

### evidence
- Operator explicitly answered yes to enabling Machinery for this lane.

### proof
- [ ] Story #1: Brownfield frame recorded.
- [ ] Story #2: Domain entities and lifecycles complete.
- [ ] Story #3: Positive and negative invariants complete.
- [ ] Story #4: Edge and failure scenarios complete.
- [ ] Story #5: Architecture boundaries and postures complete.
- [ ] Story #6: Machine and oracle complete.
- [ ] Story #7: Hard-TDD BUILD plan complete.
- [ ] Story #8: Deterministic phase gates pass.

## Acceptance Criteria


## Design


## Notes


## History
- 2026-09-20T19:50:05Z dep_added: blocks CSR-ho03
- 2026-09-20T19:51:07Z status: open -> in_progress
- 2026-09-20T19:51:07Z claimed by dev-CSR-97nc

## Links
- Parent: [[CSR-jg64]]
- Blocks: [[CSR-ho03]]

## Comments
