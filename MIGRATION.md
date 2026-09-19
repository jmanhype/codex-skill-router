# Codex Skill Router source migration

This repository is the canonical source snapshot for the accepted local Codex
Skill Router implementation that was previously maintained only under:

```text
/Users/speed/.codex/skill-router
```

## Migration boundary

The live directory remains the deployed machine-global runtime. This first
migration intentionally does not change the registered Codex hook or mutate the
live SQLite index/telemetry. `MIGRATION.sha256` records the exact accepted files
copied into this repository.

The following runtime state is intentionally untracked:

- `skills.sqlite3`
- `events.jsonl`
- `feedback.jsonl`

The accepted 50-prompt calibration report is tracked under `reports/` because
its schema records prompt hashes and aggregate data, not raw prompt text. One
accepted runtime event is tracked as the privacy-preserving regression fixture
`fixtures/events.jsonl`; `test_feedback.py` was adjusted to read that fixture
instead of requiring machine-local telemetry in the source checkout.

The canonical checkout also normalizes one trailing-whitespace defect in
`report.py`. `MIGRATION.sha256` preserves the exact live accepted hashes before
that migration-only hygiene change.

## Current limitation

The accepted `config.json` and several regression tests intentionally encode
this operator's absolute skill roots and live runtime paths. That preserves the
accepted behavior and evidence, but a fresh clone cannot yet run the full
machine-specific suite without the same local installation. A follow-up story
should add a portable configuration template and deployment/hash guard before
changing the live hook path.

## Verification used for this snapshot

```bash
/usr/bin/python3 -m unittest discover -s /Users/speed/.codex/skill-router \
  -p 'test_*.py' -v
```

Result:

```text
Ran 27 tests in 0.792s
OK
```
