# BUILD: Codex Skill Router Global Artifact Guard

Mode: full (self-contained over the `design/` tree)

## 1. Purpose and scope

Implement a Python standard-library transaction guard that stages repository-owned bytes immutably, verifies source/live-pre/post SHA-256 values, acquires one exclusive lease per temporary or live root, atomically installs the complete declared set or restores captured pre-state, and appends terminal audit evidence. This design intentionally does not deploy or re-register the live hook.

In scope:

- one `artifact_guard.py` module and CLI;
- typed transaction/stage/lease/audit records;
- real temporary-root filesystem integration tests;
- concurrent acquisition, stale-hash, commit failure, rollback, crash recovery, and audit failure coverage;
- verify-only live-root inspection that writes nothing.

Out of scope:

- arbitrary skill execution;
- router ranking behavior;
- live hook registration or deployment;
- new third-party dependencies.

## 2. Domain and architecture

The canonical data model is `design/domain.modelith.yaml`. The C4 model and Architecture Contract are `design/workspace.dsl` and `design/ARCHITECTURE.md`. Code must not redefine their vocabulary or boundaries.

## 3. State machines

| Machine | Matrix | Oracle |
|---|---|---|
| `Artifact` | `Artifact.matrix.md` | `Artifact.oracle.md` |
| `StagedArtifact` | `StagedArtifact.matrix.md` | `StagedArtifact.oracle.md` |
| `HashExpectation` | `HashExpectation.matrix.md` | `HashExpectation.oracle.md` |
| `Lease` | `Lease.matrix.md` | `Lease.oracle.md` |
| `AuditRecord` | `AuditRecord.matrix.md` | `AuditRecord.oracle.md` |
| `ArtifactTransaction` | `ArtifactTransaction.matrix.md` | `ArtifactTransaction.oracle.md` |

There are 30 transition oracle rows. The machine JSON is transition authority; matrices define named-unit contracts and failure handling.

## 4. Traceability matrix

| invariant | Enforcement | Oracle and additional tests |
|---|---|---|
| `artifact-source-pinned` | artifact source/target declaration validation | `ARTF-166f17`; repository containment property |
| `live-artifact-byte-bound` | only transaction commit/rollback writes targets | `TXN-fe36a0`, `TXN-5fd1c7`; byte-for-byte pre/post checks |
| `stage-immutable` | read-only content-addressed stage mode and hash | `STAG-8af0e4`, `STAG-910d99`, `STAG-cfb530` |
| `stage-content-addressed` | stage path derived from SHA-256 | `TXN-0ce397`; duplicate-byte property |
| `hash-comparison-explicit` | every source/pre/post digest represented | `HASH-08bd15`, `HASH-f9bb6c` |
| `stale-hash-rejected` | pre-hash mismatch rejects before mutation | `TXN-92359e`; changed-live-file integration |
| `lease-exclusive` | atomic compare-and-create lease | `LEAS-07f187`, `TXN-07ee49`; two-process contention |
| `orphan-recovery-bounded` | expiry plus recovery audit | `LEAS-941578`, `LEAS-d276b5`, `TXN-896a3d` |
| `guard-fail-closed` | rejection leaves targets byte-identical | `TXN-78feea`, `TXN-07ee49`, `TXN-92359e`, `TXN-c5c4ad` |
| `commit-atomic` | complete set or complete pre-state | `TXN-fe36a0`, `TXN-f9d923`; multi-target failure |
| `rollback-prestate-only` | only captured bytes/modes restored | `TXN-d8cb41`, `ARTF-4519af` |
| `post-hash-bound` | installed digest recorded | `TXN-fe36a0`, `ARTF-8526af` |
| `audit-complete` | one durable terminal record | `AUDI-39c46c`, `AUDI-da531b`; audit failure rollback |

## 5. Test specification

The implementation must parse all six oracle Markdown files at runtime and key one hard-TDD test on every stable id:

```text
ARTF-166f17 ARTF-8526af ARTF-4519af
STAG-8af0e4 STAG-cfb530 STAG-910d99
HASH-f9bb6c HASH-08bd15
LEAS-07f187 LEAS-60ee49 LEAS-941578 LEAS-d276b5
AUDI-39c46c AUDI-da531b
TXN-0ce397 TXN-78feea TXN-55eac5 TXN-07ee49 TXN-3958f3
TXN-f69729 TXN-92359e TXN-896a3d TXN-fe36a0 TXN-f9d923
TXN-c06d44 TXN-d8cb41 TXN-5fd1c7 TXN-bbca31 TXN-305eaa TXN-c5c4ad
```

Integration tests must use real temporary directories and real files. No mock filesystem. Concurrency must use at least two real processes or threads racing acquisition and assert exactly one winner. Live-root verification must compare a before/after manifest and prove zero writes.

## 6. State migration

No persisted transaction state exists yet. Initial storage consists only of immutable stages, lease metadata, captured pre-state, and append-only audit records. Unknown persisted status values fail loudly; silent coercion is forbidden.

## 7. Build plan

**M0 - Oracle-bound walking skeleton**

Implement typed records, state-transition dispatch, oracle parsers, and deterministic in-memory/temporary-directory fixtures for all 30 rows.

DoD: every stable id above appears whole-token in passing tests, including `TXN-0ce397`, `TXN-55eac5`, `TXN-fe36a0`, `STAG-cfb530`, `HASH-f9bb6c`, `LEAS-07f187`, and `AUDI-39c46c`; `machinery check design --impl .` has zero blocking findings; all existing router tests pass; no live-root mutation.
Status: open

**M1 - Real filesystem transaction semantics**

Implement content-addressed immutable staging, source/live-pre/post hashing, pre-state capture, atomic replacement, rollback, and append-only audit.

DoD: `TXN-0ce397`, `TXN-55eac5`, `TXN-f69729`, `TXN-fe36a0`, `TXN-f9d923`, `TXN-c06d44`, and `TXN-5fd1c7` pass against real temporary roots; a forced multi-target failure restores exact bytes and modes.
Status: open

**M2 - Contention, recovery, and verify-only closure**

Implement exclusive lease acquisition, loser safety, stale-hash rejection, bounded orphan recovery, CLI output, and read-only live-root verification.

DoD: `TXN-07ee49`, `TXN-92359e`, `TXN-896a3d`, `TXN-d8cb41`, `TXN-bbca31`, `TXN-305eaa`, and `TXN-c5c4ad` pass; concurrent acquisition yields exactly one winner; live-root before/after manifest is byte-identical; full suite and CI pass.
Status: open

## 8. Toolchain

- Language: Python 3 standard library only.
- Runtime: the installed `/usr/bin/python3` used by the repository test suite.
- Test framework: `unittest` discovery through `test_*.py`.
- Filesystem: POSIX local filesystem semantics with `os.replace` atomic replacement.
- Concurrency: real process or thread contention tests; no mock filesystem.

## 9. Language realization notes

Use Python 3 standard library only: `pathlib`, `hashlib`, `json`, `os`, `tempfile`, `threading`/`multiprocessing`, and `unittest`. Atomic replacement must account for cross-filesystem temporary paths. Lease acquisition must use exclusive create semantics. No skill or hook is executed.
