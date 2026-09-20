# Machinery Decisions

2026-09-20 Operator: enabled `design.machinery=on` for the Skill Router global-artifact guard lane.
2026-09-20 Operator/conductor: classified the run as Python brownfield; improve the canonical checkout in place and do not replace the router.
2026-09-20 Operator/conductor: live deployment is out of scope for CSR-97nc; tests use temporary roots and must not mutate `/Users/speed/.codex/skill-router` or `/Users/speed/.codex/hooks.json`.
2026-09-20 Conductor: modeled one `Transaction` aggregate owning artifact staging, one root lease, atomic commit/rollback, and terminal audit evidence.
2026-09-20 Conductor: staged bytes are immutable and content-addressed; the live pre-hash must be verified after lease acquisition or immediately before commit in the same exclusive critical section.

# Author-proposed, unconfirmed

- Stages may be retained as immutable evidence after rejection or rollback.
- Lease recovery is permitted only after a declared expiry and requires a fresh pre-hash verification.
