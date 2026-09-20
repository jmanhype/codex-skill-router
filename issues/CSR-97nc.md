---
id: CSR-97nc
title: "Machinery: design fail-closed global artifact transaction"
status: closed
priority: 0
type: task
labels: [machinery, security, accepted]
parent: CSR-jg64
created_at: 2026-09-20T19:50:05Z
created_by: speed
updated_at: 2026-09-20T20:43:46Z
content_hash: "sha256:4ded980ec9fddaf2eb369190f0a17812fe83673109fac54f5f7fd3c098dddc9a"
assignee: dev-CSR-97nc
closed_at: 2026-09-20T20:43:46Z
close_reason: "Accepted: complete brownfield Machinery design and 30-row hard-TDD oracle with all deterministic gates and CI green."
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
## PM Decision
ACCEPTED [2026-09-20]: Independently reviewed all 25 design files, reran Modelith, Machinery gc/g2/g3/gx/gb, oracle generation, backlog lint, and the existing 31-test router suite. PR 2 required CI passed with CLEAN merge state and no review threads. Generated Machinery artifacts account for the story-line overrun; the design scope remained bounded.

## nd_contract
status: delivered

### evidence
- Transitioned via pvg story deliver on 2026-09-20.

### proof
- [ ] Developer evidence block must remain authoritative above this contract.


## Implementation Evidence

Commands run:

- `modelith lint design/domain.modelith.yaml` - 0 errors, 0 warnings.
- `machinery check design --gate gc,g2,g3,gx,gb` - 0 blocking findings.
- `machinery oracle design/machines` - six fresh oracles, 30 total transition rows.
- `pvg lint --backlog` - 0 errors.
- `/usr/bin/python3 -m unittest discover -s . -p 'test_*.py' -q` - 31 tests OK.
- `git diff --check` and `git diff --cached --check` - pass.

### CI/Test Results

- Gc: 13 invariants declared, 60 preserves references, 13 carried.
- G2: 3 boundaries, 1 external, contract and dependency rules green.
- G3: 6 machines, 30 transitions, 6 fresh oracles, 27 named units.
- Gx: 6 lifecycle entities traced, 13/13 invariants unit-backed.
- Gb: 3 milestones, 3 DoD-bearing milestones, 7 skeleton citations.
- Existing router suite: 31/31 passed.

### AC Verification

| AC | Result | Evidence |
|---|---|---|
| 1. Python brownfield frame | PASS | DECISIONS.md records language, mode, and live deployment exclusion. |
| 2. Complete domain entities | PASS | Six lifecycle entities with statuses, attributes, relationships, actions, and scenarios. |
| 3. Positive/negative invariants | PASS | 13 invariants carried and traced. |
| 4. Edge/failure scenarios | PASS | Uncontested, stale, concurrent, rollback, recovery, and no-execution scenarios. |
| 5. Architecture boundaries | PASS | workspace.dsl and Architecture Contract pass G2. |
| 6. Machine/oracle | PASS | Six machines and six fresh oracles pass G3. |
| 7. Hard-TDD BUILD | PASS | BUILD.md cites all 30 stable IDs and passes Gb. |
| 8. Deterministic phase gates | PASS | Modelith plus Machinery gc/g2/g3/gx/gb have zero blocking findings. |

Summary: completed the Machinery design for immutable staging, explicit hashes, exclusive lease, atomic commit/rollback, bounded recovery, and audit evidence without mutating the live root.

Commit SHA: 50f0e8c1303a5f07aad9accba2a8bccf131984af

## nd_contract
status: delivered

### evidence
- Required design and router command outputs above.
- Commit `50f0e8c1303a5f07aad9accba2a8bccf131984af`.

### proof
- [x] AC #1: Brownfield frame recorded.
- [x] AC #2: Domain entities and lifecycles complete.
- [x] AC #3: Positive and negative invariants complete.
- [x] AC #4: Edge and failure scenarios complete.
- [x] AC #5: Architecture boundaries and postures complete.
- [x] AC #6: Machines and oracles complete.
- [x] AC #7: Hard-TDD BUILD plan complete.
- [x] AC #8: Deterministic phase gates pass.

## History
- 2026-09-20T19:50:05Z dep_added: blocks CSR-ho03
- 2026-09-20T19:51:07Z status: open -> in_progress
- 2026-09-20T19:51:07Z claimed by dev-CSR-97nc
- 2026-09-20T20:42:45Z status: in_progress -> in_progress
- 2026-09-20T20:43:46Z status: in_progress -> closed
- 2026-09-20T20:43:46Z dep_removed: no_longer_blocks CSR-ho03

## Links
- Parent: [[CSR-jg64]]

## Comments
