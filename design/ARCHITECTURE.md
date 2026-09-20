# Architecture: Codex Skill Router Artifact Guard

Status: Machinery Phase 2 for CSR-97nc
Model source: `design/domain.modelith.yaml`
C4 source: `design/workspace.dsl`

## Phase 0 frame

This is a **Python brownfield** design inside the stdlib-only Codex Skill Router checkout. It adds a local transaction boundary for selected machine-global files under `/Users/speed/.codex/skill-router`. The design does not deploy or re-register the live hook. Production implementation and all integration tests use temporary roots; a live-root check is verify-only and writes nothing.

## Architectural decisions

1. The guard is a transaction boundary, not a general deployment system.
2. Canonical bytes are staged first and become immutable, content-addressed evidence.
3. Expected source, observed live pre-state, staged, and installed post-state hashes are explicit.
4. One root has at most one active lease; losing concurrent writers fail closed.
5. Commit replaces the complete declared set atomically or restores the captured pre-state.
6. Audit append failure forces rollback.
7. No guard API selects, executes, or interprets a Codex skill.

## Boundary responsibilities

| Boundary | Owns | Must not do |
|---|---|---|
| `guard` | Transaction lifecycle, hash verification, exclusive lease, atomic replacement, rollback, audit append | Execute skills, mutate undeclared files, cure a stale hash, or bypass audit |
| `source` | Immutable repository-owned source bytes and accepted hash precedent | Write the live root or generate deployment state |
| `stage` | Content-addressed immutable bytes and stage provenance | Accept mutation after sealing |
| `lease` | Compare-and-set ownership, owner token, expiry | Promote a transaction without pre-hash reverification |
| `audit` | Append-only terminal outcome and hash bundle | Overwrite history or store secrets/raw prompts |
| `tests` | Real temporary-root integration, contention, rollback, and recovery coverage | Touch `/Users/speed/.codex/skill-router`, registered hooks, credentials, or arbitrary skills |

## Modelith action ownership

| Modelith action | Owning C4 element |
|---|---|
| `Artifact.select`, `Artifact.markCommitted`, `Artifact.markReverted` | `guard` |
| `StagedArtifact.seal`, `StagedArtifact.reject`, `StagedArtifact.retire` | `guard` using `stage` |
| `HashExpectation.verify`, `HashExpectation.mismatch` | `guard` |
| `Lease.acquire`, `Lease.release`, `Lease.recoverOrphan` | `guard` using `lease` |
| `Transaction.propose`, `.stage`, `.acquireLease`, `.commit`, `.rollback`, `.reject`, `.recover` | `guard` |
| `AuditRecord.append`, `AuditRecord.rejectAppend` | `guard` using `audit` |

## Event Contract

Enumeration source: `design/domain.modelith.yaml` Transaction and AuditRecord actions. The first implementation is in-process and uses an append-only JSONL terminal record rather than a broker.

| event | producer | consumer | payload by Modelith reference | delivery | ordering | dedupe key |
|---|---|---|---|---|---|---|
| `TRANSACTION_REJECTED` | `guard` | `audit` | Transaction.transactionId, rejectionCode; HashExpectation expected/observed hashes | at-least-once append | per transaction terminal | transactionId + outcome |
| `TRANSACTION_COMMITTED` | `guard` | `audit` | Transaction.transactionId; Artifact target; HashExpectation post hashes | exactly-once-effect | per transaction terminal | transactionId |
| `TRANSACTION_ROLLED_BACK` | `guard` | `audit` | Transaction.transactionId; rollback HashExpectation pre-state hashes | at-least-once append | per transaction terminal | transactionId + rollback attempt |
| `LEASE_ORPHAN_RECOVERED` | Operator through `guard` | `audit` | Lease.leaseId, ownerToken hash, expiresAt; fresh Transaction.transactionId | at-least-once append | per lease recovery | leaseId + expiresAt |

## Dependency mitigation posture

| dependency | failure modes | deployment mitigation | residual behavior | bound | operator signal |
|---|---|---|---|---|---|
| `liveRoot` | missing file, changed bytes, permission failure, filesystem full, cross-filesystem rename failure | expected pre-hash, captured pre-state, atomic replace, rollback | reject or roll back; no partial commit | declared target set only | stable rejection code and hashes |
| `lease` | stale owner, abrupt process death, clock leap | owner token, monotonic lease ID, declared expiry, audited recovery | fresh writer must reverify current hashes | one active lease per root | lease owner/expiry evidence |
| `stage` | hash mismatch, unreadable source, duplicated stage ID | SHA-256 content address and read-only immutable stage | reject before lease | complete declared source set | staged hash |
| `audit` | append failure, unwritable directory | terminal append before success is reported; rollback on failure | transaction fails closed | one record per terminal outcome | audit path and record hash |
| `source` | dirty checkout, path escapes repository, ambiguous accepted source | repository containment and source hash | reject proposal | repository-owned paths only | source path and hash |

## NFR record

- **Security:** declared targets only, repository containment, no credentials in stages or audit, no arbitrary execution, verify-only live-root mode.
- **Reliability:** one active lease, atomic commit, complete pre-state rollback, durable terminal audit.
- **Portability:** Python standard library only; all mutation tests use temporary roots.
- **Observability:** every terminal outcome carries stable rejection/success code and source/pre/post hashes.
- **Recoverability:** stale lease recovery is bounded and cannot promote stale bytes without a fresh live-hash check.

## Architecture Contract

```yaml
contract_version: 2
boundaries:
  - id: csr.artifact-guard
    kind: component
    element: guard
    code: ["artifact_guard.py"]
    exposes: ["artifact_guard.py"]
    provides: ["guarded-artifact-transaction"]
    consumes: ["canonical-source"]
  - id: csr.canonical-source
    kind: component
    element: source
    code: ["*.py", "*.md", "*.json", "HASHES.sha256", "MIGRATION.sha256"]
    exposes: ["*.py", "*.md", "*.json", "HASHES.sha256", "MIGRATION.sha256"]
    provides: ["canonical-source"]
  - id: csr.test-harness
    kind: component
    element: tests
    code: ["test_*.py"]
    exposes: ["test_*.py"]
    provides: ["portable-guard-tests"]
    consumes: ["guarded-artifact-transaction"]
externals:
  - id: external.live-global-root
    element: liveRoot
    imports: []
ignore:
  - ".git/**"
  - ".github/**"
  - ".paivot/**"
  - ".vault/**"
  - "design/**"
  - "fixtures/**"
  - "reports/**"
dependency_rules:
  allow:
    - csr.artifact-guard -> csr.canonical-source
    - csr.artifact-guard -> external.live-global-root
    - csr.test-harness -> csr.artifact-guard
  deny:
    - csr.canonical-source -> external.live-global-root
    - csr.canonical-source -> csr.artifact-guard
  assert:
    - no_path: csr.canonical-source -> external.live-global-root
```
