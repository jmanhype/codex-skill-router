---
id: CSR-ho03
title: "Implement hash/lease artifact guard from Machinery oracle"
status: open
priority: 0
type: task
labels: [security, implementation, capstone, external-integration]
parent: CSR-jg64
created_at: 2026-09-20T19:50:05Z
created_by: speed
updated_at: 2026-09-20T19:50:36Z
content_hash: "sha256:5f70e9b25feb4b904b2c6554e8a3585c337d9ca21ae6bd178e72aaa8c5fe092d"
blocked_by: [CSR-97nc]
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


## History
- 2026-09-20T19:50:05Z dep_added: blocked_by CSR-97nc

## Links
- Parent: [[CSR-jg64]]
- Blocked by: [[CSR-97nc]]

## Comments
