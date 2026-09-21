---
id: CSR-jg64
title: "Guard machine-global Skill Router artifacts"
status: closed
priority: 0
type: epic
labels: [security, machinery]
created_at: 2026-09-20T19:50:05Z
created_by: speed
updated_at: 2026-09-21T00:45:03Z
content_hash: "sha256:d6e0287f3f9c59c0a1b295940752a7f15f32cf0cad1a10f2dac8438c5a38b280"
closed_at: 2026-09-21T00:45:03Z
close_reason: "Epic complete: both children accepted. CSR-97nc (Machinery fail-closed artifact-transaction design, PR #2) and CSR-ho03 (hash/lease artifact guard, PR #3 squash 2cf38c58) closed with recorded evidence. Guard verified at 48 targeted tests (30 subtests) covering concurrency, mismatch, stale-hash/lease and rollback, plus an independently repeated read-only live-root smoke with writes=0 and an unchanged live-root hash. Required CI green on main; no live-hook deployment."
---

## Description
## USER INTENT
The operator wants concurrent Codex sessions to mutate machine-global Skill Router artifacts only through an immutable, hash-guarded, singly leased transaction.

## Epic Outcomes
- Machinery models the global artifact transaction before implementation.
- The guard stages immutable artifacts, verifies expected pre-hashes, acquires one lease, commits or rolls back atomically, and records post-hashes.
- Stale hashes and concurrent leases fail closed.
- The live deployed hook is not changed without a separate explicit deployment decision.

## OUT OF SCOPE
- Arbitrary skill execution.
- Router ranking behavior changes.
- Deploying or re-registering the live Codex hook.
- Moving runtime SQLite/events/feedback state into Git.

## nd_contract
status: new

### evidence
- Operator explicitly enabled `design.machinery=on` for this Skill Router guard lane on 2026-09-20.

### proof
- [ ] Pending Machinery design and implementation story acceptance.

## Acceptance Criteria


## Design


## Notes


## History
- 2026-09-21T00:45:03Z status: open -> closed

## Links


## Comments
