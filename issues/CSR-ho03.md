---
id: CSR-ho03
title: "Implement hash/lease artifact guard from Machinery oracle"
status: closed
priority: 0
type: task
labels: [security, implementation, capstone, external-integration, delivered]
parent: CSR-jg64
created_at: 2026-09-20T19:50:05Z
created_by: speed
updated_at: 2026-09-20T22:53:27Z
content_hash: "sha256:4e2d226e71aef546ca08af2cc8e52745b7e3e41a1527de152d0f2511fd04d154"
was_blocked_by: [CSR-97nc]
follows: [CSR-97nc]
closed_at: 2026-09-20T22:53:27Z
close_reason: "PM closeout applied after rework: commit cbcea9f83865274bdaaee555909aa2447683dee7 passes 48/48 targeted and 79/79 full tests, Machinery/pvg/verifier/diff gates, and an independently repeated read-only live-root smoke (15/15 manifest entries unchanged; 13 eligible hashes matched; writes=0). Seven Qodo findings were fixed, the remaining finding was refuted with a strengthened state assertion, all eight threads are resolved with evidence, and required PR 3 CI passed at https://github.com/jmanhype/codex-skill-router/actions/runs/35542919033/job/106163706272. PR merge state is CLEAN. Branch diff is 798 insertions with no live-root deployment."
---

## Description
## USER INTENT
Concurrent Codex workers need a tested production guard that refuses to overwrite machine-global Skill Router artifacts unless staged bytes, expected hashes, and a single lease all match.

## Context (Embedded)
Implementation follows the accepted Machinery design. It must be portable in CI while targeting the operator live root. Tests use temporary roots and temporary global directories; they must not mutate `/Users/speed/.codex/skill-router` or the registered hook.

## OUT OF SCOPE
- Deploying or re-registering the live hook.
- Arbitrary skill execution.
- Router ranking behavior.
- New third-party dependencies.
- Mutating the operator live root during tests.

## DIFF BUDGET
- ~6 files, under 900 changed LOC.

## Boundary Map
PRODUCES:
- artifact_guard.py -> typed staged hash/lease transaction API and CLI
- test_artifact_guard.py -> real filesystem and concurrency tests
- design/acceptance/M0.yaml -> closed Machinery milestone evidence

CONSUMES:
- design/machines/ArtifactTransaction.oracle.md -> canonical transition oracle
  schema: generated Markdown oracle rows with content-derived stable IDs
- MIGRATION.md -> live-root boundary
  schema: Markdown canonical/live deployment boundary

## Story Contract
The user can run a temporary-root integration suite that stores exactly one atomic guarded commit and rejects stale or concurrently leased writers without mutating the live root.

1. Staged artifacts are content-addressed, immutable, and validated against declared expected SHA-256 hashes before lease acquisition.
2. A stale live hash prevents lease acquisition and commit.
3. Exactly one active lease per global root is enforced under concurrent acquisition.
4. Losing concurrent writers fail closed without deleting the winner's staged bytes.
5. Commit writes through atomic replace and records post-hashes.
6. Commit failure rolls back to the recorded pre-state without partial files.
7. Crash-orphan recovery is explicit, auditable, and cannot promote a stale transaction.
8. Every transition is covered by tests citing the accepted oracle stable IDs verbatim.
9. Full local suite and CI pass without live-root mutation.
10. A manual read-only live-root smoke verification displays the current eligible SHA-256 baseline and proves no file is created, modified, or deleted; it does not acquire a lease or deploy a hook.

## Testing Requirements
- `/usr/bin/python3 -m unittest -v test_artifact_guard.py`
- `/usr/bin/python3 -m unittest discover -s . -p 'test_*.py' -v`
- `/usr/bin/python3 artifact_guard.py --root /Users/speed/.codex/skill-router --verify-only`
- `machinery check design --impl .`
- `pvg gates`
- `git diff --check`

## MANDATORY SKILLS
- pvg
- developer

## nd_contract
status: new

### evidence
- Implementation is blocked until the Machinery design story is accepted.

### proof
- [ ] Story #1: Immutable validated staging.
- [ ] Story #2: Stale-hash rejection.
- [ ] Story #3: Single lease under concurrency.
- [ ] Story #4: Concurrent loser safety.
- [ ] Story #5: Atomic commit and post-hash audit.
- [ ] Story #6: Rollback preservation.
- [ ] Story #7: Safe orphan recovery.
- [ ] Story #8: Oracle-cited transition coverage.
- [ ] Story #9: Full local/CI gates and no live mutation.

## USER INTENT
Concurrent Codex workers need a tested production guard that refuses to overwrite machine-global Skill Router artifacts unless staged bytes, expected hashes, and a single lease all match.

## Context (Embedded)
Implementation follows the accepted Machinery design. It must be portable in CI while targeting the operator live root. Tests use temporary roots and temporary global directories; they must not mutate `/Users/speed/.codex/skill-router` or the registered hook.

## OUT OF SCOPE
- Deploying or re-registering the live hook.
- Arbitrary skill execution.
- Router ranking behavior.
- New third-party dependencies.
- Mutating the operator live root during tests.

## DIFF BUDGET
- ~6 files, under 900 changed LOC.

## Boundary Map
PRODUCES:
- artifact_guard.py -> typed staged hash/lease transaction API and CLI
- test_artifact_guard.py -> real filesystem and concurrency tests
- design/acceptance/M0.yaml -> closed Machinery milestone evidence

CONSUMES:
- design/machines/ArtifactTransaction.oracle.md -> canonical transition oracle
  schema: generated Markdown oracle rows with content-derived stable IDs
- MIGRATION.md -> live-root boundary
  schema: Markdown canonical/live deployment boundary

## Story Contract
The user can run a temporary-root integration suite that stores exactly one atomic guarded commit and rejects stale or concurrently leased writers without mutating the live root.

1. Staged artifacts are content-addressed, immutable, and validated against declared expected SHA-256 hashes before lease acquisition.
2. A stale live hash prevents lease acquisition and commit.
3. Exactly one active lease per global root is enforced under concurrent acquisition.
4. Losing concurrent writers fail closed without deleting the winner's staged bytes.
5. Commit writes through atomic replace and records post-hashes.
6. Commit failure rolls back to the recorded pre-state without partial files.
7. Crash-orphan recovery is explicit, auditable, and cannot promote a stale transaction.
8. Every transition is covered by tests citing the accepted oracle stable IDs verbatim.
9. Full local suite and CI pass without live-root mutation.

## Testing Requirements
- `/usr/bin/python3 -m unittest -v test_artifact_guard.py`
- `/usr/bin/python3 -m unittest discover -s . -p 'test_*.py' -v`
- `machinery check design --impl .`
- `pvg gates`
- `git diff --check`

## MANDATORY SKILLS
- pvg
- developer

## nd_contract
status: new

### evidence
- Implementation is blocked until the Machinery design story is accepted.

### proof
- [ ] Story #1: Immutable validated staging.
- [ ] Story #2: Stale-hash rejection.
- [ ] Story #3: Single lease under concurrency.
- [ ] Story #4: Concurrent loser safety.
- [ ] Story #5: Atomic commit and post-hash audit.
- [ ] Story #6: Rollback preservation.
- [ ] Story #7: Safe orphan recovery.
- [ ] Story #8: Oracle-cited transition coverage.
- [ ] Story #9: Full local/CI gates and no live mutation.

## Acceptance Criteria


## Design


## Notes


## nd_contract
status: delivered

### evidence
- Transitioned via pvg story deliver on 2026-09-20.

### proof
- [ ] Developer evidence block must remain authoritative above this contract.


## PM Rework Evidence

Qodo security/reliability review was independently validated; seven findings were fixed and finding #7 was refuted by strengthening an existing assertion.

Commands rerun after rework:

- `/usr/bin/python3 -m unittest -v test_artifact_guard.py` — 48/48 passed.
- `/usr/bin/python3 -m unittest discover -s . -p 'test_*.py' -q` — 79/79 passed.
- `machinery check design --impl .` — zero blocking findings.
- `pvg gates` — PASS with seven pre-existing warnings only.
- `pvg verify artifact_guard.py test_artifact_guard.py --include-tests --format=text` — PASSED.
- `git diff --check` — passed.
- Read-only live-root smoke independently rerun — 15/15 full-root manifest entries byte-identical before/after; 13 eligible hashes all matched; writes=0.

Regressions added/extended for partial replacement recovery, expired-owner leases, partial capture, stable stage failures, malformed audit JSON, post-validation parent swaps, staged-to-committed state assertion, and unsafe-recovery audit.

Final branch diff from main: 798 insertions total across two files, under 900 LOC.

Commit SHA: cbcea9f83865274bdaaee555909aa2447683dee7
artifact_guard.py SHA-256: 46c9ee2dd7593ff83bef34140d8fe2ab777bfb54b1987f474acc3d50d29f7345
test_artifact_guard.py SHA-256: 2a973c4790fc15700083ac61383ee7e718b4de1d19137e8cfe313168e60732a1

## nd_contract
status: delivered

### evidence
- Rework commit `cbcea9f83865274bdaaee555909aa2447683dee7` and independently rerun local/live-root evidence above.

### proof
- [x] AC #1: Immutable validated staging.
- [x] AC #2: Stale-hash rejection.
- [x] AC #3: Single lease under concurrency.
- [x] AC #4: Concurrent loser safety.
- [x] AC #5: Atomic commit and post-hash audit.
- [x] AC #6: Rollback preservation.
- [x] AC #7: Safe orphan recovery, including abrupt expired-owner and partial-replacement cases.
- [x] AC #8: All 30 oracle transitions covered by stable ID.
- [x] AC #9: Full local gates pass; live root remains unchanged; required PR CI must pass before PM closeout.

## nd_contract
status: rejected

### evidence
- PM rejection applied via pvg story reject on 2026-09-20.

### proof
- [ ] Story requires another developer delivery before it can be accepted.


## nd_contract
status: accepted

### evidence
- PM closeout applied via pvg story accept on 2026-09-20.

### proof
- [x] Story closed after accepted label was applied.


## nd_contract
status: delivered

### evidence
- Transitioned via pvg story deliver on 2026-09-20.

### proof
- [ ] Developer evidence block must remain authoritative above this contract.


## Implementation Evidence

Commands run:

- `/usr/bin/python3 -m unittest -v test_artifact_guard.py` - 42 passed.
- `/usr/bin/python3 -m unittest discover -s . -p 'test_*.py' -q` - 73 passed.
- `machinery check design --impl .` - Gc/G2/G3/Gx/Gb/G4/Gt all zero blocking findings.
- `pvg gates` - PASS with pre-existing warnings only.
- `pvg verify artifact_guard.py test_artifact_guard.py --include-tests --format=text` - 2 files, 0 issues.
- Read-only live-root CLI - eligible_count 13, all_matched true, writes 0; full 15-file live manifest was byte-for-byte identical before/after.
- `git diff --check` and `git diff --cached --check` - pass.

### CI/Test Results

- All 30 Machinery stable oracle IDs appear literally in passing tests.
- Real temporary-root integration coverage includes immutable content-addressed staging, source/pre/post hashes, stale hash, exclusive concurrent lease, loser safety, atomic commit, complete pre-state rollback, audit failure rollback, bounded recovery, and verify-only zero writes.
- Concurrency hardening includes O_EXCL reservation, fail-closed unreadable lease metadata, flock plus in-process locking, and 20 repeated contention runs during development.
- Independent PM review added and passed a parent-symlink escape regression.
- No live hook/root mutation, arbitrary skill execution, ranking change, or third-party dependency.

### AC Verification

| AC | Result | Evidence |
|---|---|---|
| 1. Immutable validated staging | PASS | Content-addressed read-only stage tests. |
| 2. Stale-hash rejection | PASS | Pre-hash mismatch rejects before target mutation. |
| 3. One lease under concurrency | PASS | Real concurrent test yields exactly one winner. |
| 4. Concurrent loser safety | PASS | Loser is denied and immutable stage evidence remains. |
| 5. Atomic commit/post hashes | PASS | Complete declared-set replacement plus audit tests. |
| 6. Rollback preservation | PASS | Exact bytes and modes restored on replacement failure. |
| 7. Safe orphan recovery | PASS | Bounded expiry, fresh verification, audit; unbounded/stale refuses. |
| 8. Oracle transition coverage | PASS | Every one of 30 stable IDs is literal and passing. |
| 9. Full local/CI and no live mutation | PASS | 73/73 local; live-root verify-only manifest unchanged; PR CI required below. |

Summary: implemented the accepted Machinery design in 737 two-file lines, under the 900-line story budget.

Commit SHA: 021532ae75c8d962e6e96eef45d7aa51dab57450

## nd_contract
status: delivered

### evidence
- Required command outputs above.
- Commit `021532ae75c8d962e6e96eef45d7aa51dab57450`.

### proof
- [x] AC #1: Staged artifacts are immutable and source-hash validated.
- [x] AC #2: Stale live hashes reject.
- [x] AC #3: One active root lease wins under contention.
- [x] AC #4: Concurrent losers fail safely.
- [x] AC #5: Commit is atomic and post-hashed.
- [x] AC #6: Rollback preserves exact pre-state.
- [x] AC #7: Orphan recovery is bounded and audited.
- [x] AC #8: All oracle transitions are covered by stable ID.
- [x] AC #9: Full suite, Machinery gates, live-root verify-only, and PR CI are required.

## History
- 2026-09-20T19:50:05Z dep_added: blocked_by CSR-97nc
- 2026-09-20T20:43:46Z dep_removed: was_blocked_by CSR-97nc
- 2026-09-20T20:44:35Z status: open -> in_progress
- 2026-09-20T20:44:35Z auto-follows: linked to predecessor CSR-97nc
- 2026-09-20T20:44:35Z claimed by dev-CSR-ho03
- 2026-09-20T22:17:22Z status: in_progress -> in_progress
- 2026-09-20T22:32:34Z status: in_progress -> closed
- 2026-09-20T22:33:19Z status: closed -> open (reopened)
- 2026-09-20T22:33:19Z released by speed
- 2026-09-20T22:51:18Z status: open -> in_progress
- 2026-09-20T22:53:27Z status: in_progress -> closed

## Links
- Parent: [[CSR-jg64]]
- Was blocked by: [[CSR-97nc]]
- Follows: [[CSR-97nc]]

## Comments

### 2026-09-20T22:33:19Z speed
EXPECTED: Required PR conversation resolution and security/reliability review must be clean before acceptance. DELIVERED: PM accepted before accounting for Qodo PR review threads; GitHub remains BLOCKED because 8 threads are unresolved. GAPS: (1) crash after partial sequential replacement; (2) expired Acquired leases cannot recover after abrupt owner death; (3) partial pre-state capture can strand a lease; (4) OSError during stage lacks stable rejection code; (5) malformed audit JSON can bypass AuditAppendError/release; (6) parent-directory swaps after validation can escape live root; (7) successful commit skips Staged -> Committed transition; (8) unsafe recovery lacks terminal audit. FIX: reopen the story, independently validate each finding, repair true defects and add focused regressions, refute false positives with code/tests, rerun required tests/gates/live read-only smoke, update the same PR, and resolve all conversation threads only with evidence. Acceptance is premature until merge state is CLEAN.
