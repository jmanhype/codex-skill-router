---
id: CSR-jg64
title: "Guard machine-global Skill Router artifacts"
status: open
priority: 0
type: epic
labels: [security, machinery]
created_at: 2026-09-20T19:50:05Z
created_by: speed
updated_at: 2026-09-20T19:50:05Z
content_hash: "sha256:21e3bf3a45ab73fe46dbacabfb68373520dc2a58c15a9e4cb2633a526a81a149"
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


## Links


## Comments
