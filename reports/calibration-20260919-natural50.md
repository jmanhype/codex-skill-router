# Codex Skill Router Natural-Use Calibration

- Generated: `2026-09-19T03:24:56Z`
- Prompts processed: **50**
- Source: local Codex prompt history
- Network calls: **0**
- Raw prompts persisted: **no**
- Event log modified: **no**

## Summary

| Metric | Result |
|---|---:|
| Suggestions | 35 (70.0%) |
| Abstentions | 15 (30.0%) |
| Median latency | 3.057 ms |
| p95 latency | 44.278 ms |
| Max latency | 72.310 ms |
| Literal skill-name references top-1 | 1/7 |
| Explicit skill invocations top-1 | 0/2 |
| Obvious conversational false positives | 0/2 |
| Natural prompts needing manual review | 41 |

## Candidate Distribution

| Top candidate | Count |
|---|---:|
| `last30days` | 3 |
| `Zettel Reflect` | 2 |
| `codex-computer-use` | 2 |
| `monetization-strategy` | 2 |
| `supabase-magic-link-hash-fragment` | 1 |
| `grammar-check` | 1 |
| `zhipu-osa-daemon-glm-jwt-streaming` | 1 |
| `ollama-tool-calling-models` | 1 |
| `vlt` | 1 |
| `sites-building` | 1 |
| `Presentations` | 1 |
| `resend-email-forensics` | 1 |
| `marketing-ideas` | 1 |
| `llama-cpp-256k-context-24gb-vram` | 1 |
| `flow-gen` | 1 |

## Interpretation

This is an observational local calibration, not a fully labeled accuracy benchmark. Explicit full skill-name mentions and obvious conversational prompts provide deterministic checks. Other prompts are represented only by hash and require operator review if their suggestions look inappropriate.

## Recommendation

Keep the current threshold and ranking behavior unchanged. File a focused follow-up for local explicit-invocation resolution because both detected explicit skill invocations missed the requested skill; do not tune global scoring from this observational sample alone.
