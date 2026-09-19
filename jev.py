#!/usr/bin/env python3
"""Consent-gated Jev semantic reranking for ambiguous local skill candidates."""

from __future__ import annotations

import json
import math
import os
import re
from contextlib import suppress
from typing import Any, Callable, Dict, List, Sequence
from urllib.request import Request, urlopen


JEV_ENDPOINT = "https://api.typesafe.io/v1/jev/rerank"
CONTROL_OR_SPACE_RE = re.compile(r"[\x00-\x20\x7f]+")
DEFAULT_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS = 0.18, 0.25
MAX_PROMPT_CHARS, MAX_NAME_CHARS = 512, 96
MAX_MATCHED_TERMS, MAX_MATCHED_CHARS = 8, 48
MAX_CANDIDATES, MAX_RESPONSE_BYTES = 8, 64 * 1024

Transport = Callable[..., Any]


def _settings(config: Dict[str, Any]) -> Dict[str, Any]:
    section = config.get("jev_reranking")
    if not isinstance(section, dict):
        section = config.get("jev", {})
    if not isinstance(section, dict) or section.get("enabled") is not True:
        return {"enabled": False}

    def bounded_int(name: str, default: int, maximum: int) -> int:
        value = section.get(name, default)
        with suppress(TypeError, ValueError):
            return max(1, min(maximum, int(value)))
        return default

    try:
        timeout = max(0.02, min(MAX_TIMEOUT_SECONDS, float(section.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))))
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT_SECONDS
    try:
        window = max(0.0, min(1.0, float(section.get("ambiguity_window", 0.08))))
    except (TypeError, ValueError):
        window = 0.08

    return {
        "enabled": True,
        "timeout_seconds": timeout,
        "prompt_chars": bounded_int("prompt_summary_chars", 320, MAX_PROMPT_CHARS),
        "ambiguity_window": window,
    }


def _text(value: Any, limit: int) -> str:
    return CONTROL_OR_SPACE_RE.sub(" ", str(value)).strip()[:limit]


def _number(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def should_rerank(
    candidates: Sequence[Dict[str, Any]], config: Dict[str, Any]
) -> bool:
    """Only explicitly consented reranking may run for close lexical matches."""
    settings = _settings(config)
    if not settings["enabled"] or len(candidates) < 2:
        return False
    scores = sorted((_number(item.get("score")) for item in candidates), reverse=True)
    return scores[0] - scores[1] <= settings["ambiguity_window"]


def _payload(
    prompt: str,
    candidates: Sequence[Dict[str, Any]],
    prompt_limit: int,
) -> Dict[str, Any]:
    metadata: List[Dict[str, Any]] = []
    for index, item in enumerate(candidates[:MAX_CANDIDATES]):
        metadata.append({"id": f"c{index}", "name": _text(item.get("name", ""), MAX_NAME_CHARS),
                         "score": _number(item.get("score")), "term_overlap": _number(item.get("term_overlap")),
                         "matched": [_text(term, MAX_MATCHED_CHARS)
                                     for term in (item.get("matched") or [])[:MAX_MATCHED_TERMS]]})
    return {
        "task": "skill_candidate_rerank",
        "prompt_summary": _text(prompt, prompt_limit),
        "candidates": metadata,
        "allowed_ranking": [item["id"] for item in metadata] + ["none"],
    }


def _request(payload: Dict[str, Any], api_key: str, timeout: float) -> Any:
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(
        JEV_ENDPOINT,
        data=encoded,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "codex-skill-router/1",
        },
        method="POST",
    )
    return urlopen(request, timeout=timeout)


def _ranking(response: Any) -> List[str] | None:
    try:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            return None
        decoded = json.loads(raw.decode("utf-8"))
        ranking = decoded["ranking"]
        if not isinstance(ranking, list) or not ranking:
            return None
        if any(not isinstance(item, str) for item in ranking):
            return None
        if len(set(ranking)) != len(ranking):
            return None
        if "none" in ranking:
            return ranking if ranking == ["none"] else None
        return ranking
    except Exception:
        return None


def _ordered(
    candidates: Sequence[Dict[str, Any]], ranking: Sequence[str]
) -> List[Dict[str, Any]] | None:
    by_id = {f"c{index}": item for index, item in enumerate(candidates)}
    if not ranking or any(item not in by_id for item in ranking):
        return None
    promoted_ids = set(ranking)
    promoted = [by_id[item] for item in ranking]
    remaining = [item for index, item in enumerate(candidates) if f"c{index}" not in promoted_ids]
    return promoted + remaining


def rerank(
    prompt: str,
    candidates: Sequence[Dict[str, Any]],
    config: Dict[str, Any],
    *,
    api_key: str | None = None,
    transport: Transport = _request,
) -> List[Dict[str, Any]]:
    """Return local candidates unchanged unless a valid ranking is received."""
    local = [dict(item) for item in candidates]
    if not should_rerank(candidates, config):
        return local

    key = api_key if api_key is not None else os.environ.get("TYPESAFE_API_KEY", "")
    if not key:
        return local

    settings = _settings(config)
    payload = _payload(
        prompt, candidates[:MAX_CANDIDATES], int(settings["prompt_chars"])
    )
    response: Any = None
    for attempt in range(2):
        try:
            response = transport(payload, key, settings["timeout_seconds"])
            break
        except Exception:
            if attempt == 1:
                return local

    ordering = _ranking(response)
    if ordering == ["none"]:
        return local
    result = _ordered(candidates[:MAX_CANDIDATES], ordering or [])
    return [dict(item) for item in result] if result is not None else local


__all__ = ["rerank", "should_rerank"]
