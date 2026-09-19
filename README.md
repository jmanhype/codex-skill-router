# Codex Skill Router

A local-only `UserPromptSubmit` hook that indexes installed `SKILL.md` files and injects compact advisory skill suggestions into Codex.

## Update the index

```bash
/usr/bin/python3 /Users/speed/.codex/skill-router/index_skills.py
```

## Test

```bash
/usr/bin/python3 -m unittest -v /Users/speed/.codex/skill-router/test_router.py
```

## Behavior

- Uses SQLite FTS5 on the local machine.
- Resolves unambiguous explicit requests such as `$skill-name`, `use skill skill-name`, or `skill: skill-name` before lexical ranking.
- Sends no network requests.
- Does not execute skills.
- Emits skill name, path, score, and matched terms only.
- Stores prompt SHA-256, timing, decision, and selected candidates in `events.jsonl`; never stores raw prompt text.
- Returns `{}` on abstention or every internal failure.

## Rollback

Remove the `UserPromptSubmit` entry added to `/Users/speed/.codex/hooks.json`, or restore:

```text
/Users/speed/.codex/hooks.json.pre-skill-router-20260918
```

The index and telemetry are confined to `/Users/speed/.codex/skill-router`.
