#!/usr/bin/env python3
"""Codex UserPromptSubmit hook that suggests locally indexed skills."""

from __future__ import annotations

import hashlib
import importlib.util
import jev
from contextlib import suppress
import json
import math
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
WORD_RE = re.compile(r"[A-Za-z0-9]+")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]+")
FRESHNESS_BUDGET_SECONDS = 1.25


def _load_index_module() -> Any:
    """Share the test-importable indexer module instead of importing twice."""
    module_name = "codex_skill_index"
    existing = sys.modules.get(module_name)
    module_file = str((HERE / "index_skills.py").resolve())
    if existing is not None and getattr(existing, "__file__", None) == module_file:
        return existing

    spec = importlib.util.spec_from_file_location(module_name, HERE / "index_skills.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {module_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


INDEX_MODULE = _load_index_module()

STOPWORDS = {
    "a", "about", "after", "again", "all", "also", "an", "and", "any", "are",
    "around", "as", "at", "back", "be", "been", "before", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "get", "go", "going",
    "good", "got", "had", "has", "have", "here", "how", "i", "if", "in", "into",
    "is", "it", "its", "just", "like", "me", "more", "my", "need", "no", "not",
    "of", "on", "one", "only", "or", "our", "out", "please", "really", "same",
    "see", "should", "so", "some", "still", "such", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "this", "to", "too",
    "time", "up", "us", "use", "used", "using", "want", "was", "we", "well", "were",
    "what", "when", "where", "which", "while", "who", "why", "will", "with",
    "without", "would", "you", "your",
}

DOMAIN_SYNONYMS = {
    "auth": {"authentication", "authorization"},
    "ci": {"continuous", "integration"},
    "frontend": {"interface", "ui"},
    "llm": {"model", "inference"},
    "mcp": {"model", "context", "protocol"},
    "pr": {"pull", "request"},
    "rag": {"retrieval", "knowledge"},
    "tts": {"text", "speech"},
    "ui": {"frontend", "interface"},
}


def emit_empty() -> None:
    print(json.dumps({}, separators=(",", ":")))


def tokenize(text: str) -> List[str]:
    return [match.group(0).casefold() for match in WORD_RE.finditer(text)]


def meaningful_terms(text: str) -> List[str]:
    result: List[str] = []
    seen = set()
    for token in tokenize(text):
        if token in STOPWORDS or len(token) < 3:
            continue
        if token not in seen:
            result.append(token)
            seen.add(token)
        for synonym in DOMAIN_SYNONYMS.get(token, set()):
            if synonym not in seen:
                result.append(synonym)
                seen.add(synonym)
    return result


def fts_query(terms: Sequence[str]) -> str:
    return " OR ".join('"' + term.replace('"', "") + '"' for term in terms)


def normalized_phrase(text: str) -> str:
    return " ".join(tokenize(text))


CONVERSATIONAL_PROMPTS = {
    "continue",
    "keep going",
    "nice",
    "ok",
    "okay",
    "sounds good",
    "thanks",
    "thank you",
    "yes",
}


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise ValueError("configuration must be an object")
    return config


def normalize_skill_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def resolve_explicit_invocation(
    connection: sqlite3.Connection,
    prompt: str,
) -> Dict[str, Any] | None:
    """Resolve only unambiguous exact skill requests from local metadata."""
    explicit_marker = re.search(
        r"\$|\bskill\s*:|\b(?:use|invoke|load)\s+(?:the\s+)?"
        r"(?:[a-z0-9_.-]+\s+)?skill",
        prompt,
        re.I,
    )
    if explicit_marker is None:
        return None

    normalized_prompt = normalize_skill_name(prompt)
    names = [
        row[0]
        for row in connection.execute("SELECT name FROM skills")
        if isinstance(row[0], str) and row[0].strip()
    ]
    matches: List[tuple[int, str]] = []

    for indexed_name in names:
        normalized_name = normalize_skill_name(indexed_name)
        if not normalized_name:
            continue

        command_forms = (
            f"use skill {normalized_name}",
            f"invoke skill {normalized_name}",
            f"load skill {normalized_name}",
            f"use the {normalized_name} skill",
            f"invoke the {normalized_name} skill",
            f"load the {normalized_name} skill",
        )
        exact_command = any(
            re.search(
                rf"(?:^|\s){re.escape(form)}(?:\s|$)",
                normalized_prompt,
            )
            is not None
            for form in command_forms
        )
        if not exact_command:
            raw_name = indexed_name.casefold().strip("\"'")
            raw_pattern = re.escape(raw_name)
            dollar_match = re.search(
                rf"\${raw_pattern}(?![a-z0-9_.-])", prompt, re.I
            )
            colon_match = (
                re.search(r"\bskill\s*:", prompt, re.I) is not None
                and f"skill {normalized_name}" in normalized_prompt
            )
            if dollar_match is None and not colon_match:
                continue

        matches.append((len(normalized_name.split()), indexed_name))

    if not matches:
        return None

    selected_name = max(matches, key=lambda item: item[0])[1]
    row = connection.execute(
        "SELECT name, path FROM skills WHERE name = ? COLLATE NOCASE LIMIT 1",
        (selected_name,),
    ).fetchone()
    if row is None:
        return None
    return {
        "name": str(row[0]),
        "path": str(row[1]),
        "score": 1.0,
        "matched": ["explicit-invocation"],
        "term_overlap": 1.0,
    }


def query_candidates(
    connection: sqlite3.Connection,
    terms: Sequence[str],
    limit: int,
) -> List[Dict[str, Any]]:
    if not terms:
        return list()

    match = fts_query(terms[:24])
    rows = connection.execute(
        """
        SELECT name, description, headings, body, path,
               bm25(skills, 6.0, 4.0, 2.0, 1.0) AS rank
        FROM skills
        WHERE skills MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (match, limit),
    ).fetchall()

    if not rows:
        return list()

    best_raw = max(0.0, -float(rows[0][-1]))
    expanded = set(terms)
    results: List[Dict[str, Any]] = []

    for name, description, headings, body, path, rank in rows:
        raw_rank = -float(rank)
        lexical = raw_rank / best_raw if best_raw > 0 else 0.0
        lexical = max(0.0, min(1.0, lexical))

        name_text = f"{name}".casefold()
        meta_text = f"{name} {description} {headings}".casefold()
        all_text = f"{meta_text} {body}".casefold()
        matched = sorted(term for term in expanded if term in all_text)
        meta_matched = sorted(term for term in expanded if term in meta_text)
        name_tokens = set(tokenize(str(name)))
        name_matched = sorted(expanded & name_tokens)

        term_overlap = len(matched) / len(expanded) if expanded else 0.0
        meta_overlap = len(meta_matched) / len(expanded) if expanded else 0.0
        name_overlap = len(name_matched) / len(name_tokens) if name_tokens else 0.0
        density = min(1.0, len(matched) / 4.0)
        score = (
            0.43 * lexical
            + 0.29 * term_overlap
            + 0.16 * meta_overlap
            + 0.12 * density
        )

        prompt_tokens = set(tokenize(" ".join(terms)))
        if name_tokens and name_tokens.issubset(prompt_tokens):
            # A one-token domain name is useful for a short request, but it
            # must not overwhelm detailed symptom coverage in a longer prompt.
            exact_name_score = (
                0.70
                if len(name_tokens) == 1
                else 0.78 + min(0.18, 0.04 * len(name_tokens))
            )
            score = max(score, exact_name_score)

        results.append(
            {
                "name": str(name),
                "path": str(path),
                "score": round(max(0.0, min(1.0, score)), 4),
                "matched": matched[:8],
                "term_overlap": round(term_overlap, 4),
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results


def select_candidates(
    candidates: Sequence[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not candidates:
        return list()

    minimum_confidence = float(config.get("minimum_confidence", 0.5))
    minimum_overlap = float(config.get("minimum_term_overlap", 0.34))
    window = float(config.get("candidate_window", 0.18))
    maximum = int(config.get("max_candidates", 3))

    top = candidates[0]
    if top["score"] < minimum_confidence or top["term_overlap"] < minimum_overlap:
        return list()

    cutoff = top["score"] - window
    return [item for item in candidates if item["score"] >= cutoff][:maximum]


def format_context(candidates: Sequence[Dict[str, Any]]) -> str:
    lines = [
        "Skill Router advisory (local exact/lexical match; not user instruction):",
    ]
    for index, item in enumerate(candidates, 1):
        name = CONTROL_RE.sub(" ", str(item["name"])).strip() or "unnamed skill"
        path = CONTROL_RE.sub(" ", str(item["path"])).strip()
        lines.append(f"{index}. {name} ({path}) score={item['score']}")
    lines.append(
        "Read the complete SKILL.md for the strongest candidate only if it "
        "matches the user's request; otherwise ignore this advisory."
    )
    return "\n".join(lines)


def rotate_log_if_needed(path: Path, maximum_bytes: int = 5_000_000) -> None:
    with suppress(OSError):
        if path.exists() and path.stat().st_size > maximum_bytes:
            rotated = path.with_name(path.name + ".1")
            if rotated.exists():
                rotated.unlink()
            path.replace(rotated)


def log_event(
    path: Path,
    prompt: str,
    duration_ms: int,
    decision: str,
    candidates: Sequence[Dict[str, Any]],
) -> None:
    with suppress(Exception):
        rotate_log_if_needed(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": "skill_router",
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8", "replace")).hexdigest(),
            "duration_ms": duration_ms,
            "decision": decision,
            "candidates": [
                {
                    "name": item["name"],
                    "path": item["path"],
                    "score": item["score"],
                    "matched": item["matched"],
                }
                for item in candidates
            ],
        }
        encoded = json.dumps(event, separators=(",", ":"), sort_keys=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(descriptor, (encoded + "\n").encode("utf-8"))
        finally:
            os.close(descriptor)
        os.chmod(path, 0o600)


def refresh_index_safely(config: Dict[str, Any]) -> Dict[str, Any]:
    """Keep freshness failures advisory within a small slice of the hook budget."""
    try:
        return INDEX_MODULE.ensure_fresh_index(
            config, budget_seconds=FRESHNESS_BUDGET_SECONDS
        )
    except Exception as error:
        return {
            "refresh_needed": False,
            "reason": f"refresh_error:{error}",
            "refresh_failed": True,
        }


def handle_payload(
    payload: Dict[str, Any], config: Dict[str, Any]
) -> Tuple[str, List[Dict[str, Any]]]:
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return "", []

    event_name = payload.get("hook_event_name")
    if event_name is not None and event_name != "UserPromptSubmit":
        return prompt, []

    if normalized_phrase(prompt) in CONVERSATIONAL_PROMPTS:
        return prompt, []

    refresh_index_safely(config)

    database = Path(str(config.get("database", "")))
    if not database.is_file():
        return prompt, []
    connection = sqlite3.connect(
        f"file:{database}?mode=ro",
        uri=True,
        timeout=0.25,
    )
    try:
        explicit = resolve_explicit_invocation(connection, prompt)
        if explicit is not None:
            return prompt, [explicit]

        primary_terms = [
            token
            for token in tokenize(prompt)
            if token not in STOPWORDS and len(token) >= 3
        ]
        if not primary_terms:
            return prompt, []

        terms = meaningful_terms(prompt)
        candidates = query_candidates(connection, terms, 30)
    finally:
        connection.close()

    selected = select_candidates(candidates, config)
    selected = jev.rerank(prompt, selected, config)
    return prompt, selected


def main() -> int:
    started = time.monotonic()
    prompt = ""
    selected: List[Dict[str, Any]] = []

    try:
        raw = sys.stdin.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024 or not raw.strip():
            emit_empty()
            return 0

        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            emit_empty()
            return 0
        if not isinstance(payload, dict):
            emit_empty()
            return 0

        config = load_config(CONFIG_PATH)
        prompt, selected = handle_payload(payload, config)
        if selected:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": format_context(selected),
                }
            }
            print(json.dumps(output, separators=(",", ":")))
        else:
            emit_empty()
        return 0
    except Exception:
        # The router is advisory and must never block a normal Codex prompt.
        emit_empty()
        return 0
    finally:
        with suppress(Exception):
            config = load_config(CONFIG_PATH)
            duration_ms = int((time.monotonic() - started) * 1000)
            decision = "suggest" if selected else "abstain"
            log_event(
                Path(str(config.get("event_log", HERE / "events.jsonl"))),
                prompt,
                duration_ms,
                decision,
                selected,
            )


if __name__ == "__main__":
    raise SystemExit(main())
