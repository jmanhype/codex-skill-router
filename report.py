#!/usr/bin/env python3
"""Emit a local, privacy-safe Skill Router health and quality report."""
from __future__ import annotations
import argparse, json, math, sqlite3, time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import feedback
import index_skills
HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG, DEFAULT_DATABASE = HERE / "config.json", HERE / "skills.sqlite3"
DEFAULT_EVENTS, DEFAULT_FEEDBACK = HERE / "events.jsonl", HERE / "feedback.jsonl"

def _read_events(path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not path.is_file():
        return [], {"path": str(path), "available": False, "readable": False, "state": "missing", "count": 0}
    try:
        events = feedback.load_events(path)
    except (OSError, ValueError):
        return [], {"path": str(path), "available": True, "readable": False, "state": "invalid", "count": None}
    return events, {"path": str(path), "available": True, "readable": True, "state": "ok", "count": len(events)}


def _read_feedback(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "available": False, "readable": False, "state": "missing", "record_count": 0, "verdict_counts": {}}
    try:
        records = feedback.load_feedback(path)
    except (OSError, ValueError):
        return {"path": str(path), "available": True, "readable": False, "state": "invalid", "record_count": None, "verdict_counts": None}
    counts = dict(sorted(Counter(str(item.get("verdict")) for item in records).items()))
    return {"path": str(path), "available": True, "readable": True, "state": "ok", "record_count": len(records), "verdict_counts": counts}


def _read_database(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "available": False, "readable": False, "state": "missing", "integrity": "missing"}
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=0.25)
        try:
            integrity = str(connection.execute("PRAGMA quick_check").fetchone()[0])
            metadata = {str(key): str(value) for key, value in connection.execute("SELECT key, value FROM metadata")}
            skill_count = int(connection.execute("SELECT count(*) FROM skills").fetchone()[0])
            manifest_count = int(connection.execute("SELECT count(*) FROM skill_manifest").fetchone()[0])
        finally:
            connection.close()
    except (OSError, sqlite3.Error, TypeError, ValueError, IndexError):
        return {"path": str(path), "available": True, "readable": False, "state": "invalid", "integrity": "invalid"}
    readable = integrity == "ok"
    return {
        "path": str(path), "available": True, "readable": readable,
        "state": "ok" if readable else "integrity_failed", "integrity": integrity,
        "schema_version": metadata.get("schema_version"), "skill_count": skill_count,
        "manifest_count": manifest_count, "generated_utc": metadata.get("generated_utc"),
    }


def _freshness(path: Path, roots: Sequence[str], database: Dict[str, Any]) -> Dict[str, Any]:
    if not database["available"] or not database["readable"]:
        return {"refresh_needed": True, "reason": "database_missing" if not database["available"] else "database_unreadable"}
    try:
        return dict(index_skills.index_freshness(path, roots))
    except Exception:
        return {"refresh_needed": True, "reason": "assessment_failed"}


def _latency(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    values = sorted(max(0, int(event["duration_ms"])) for event in events)
    if not values:
        return {"count": 0, "mean_ms": None, "min_ms": None, "p50_ms": None, "p90_ms": None, "p95_ms": None, "max_ms": None}
    percentile = lambda value: values[max(0, math.ceil(value * len(values)) - 1)]
    return {
        "count": len(values), "mean_ms": round(sum(values) / len(values), 3),
        "min_ms": values[0], "p50_ms": percentile(0.50), "p90_ms": percentile(0.90),
        "p95_ms": percentile(0.95), "max_ms": values[-1],
    }


def build_report(*, config_path: Path = DEFAULT_CONFIG, events_path: Optional[Path] = None, feedback_path: Optional[Path] = None, top_candidates: int = 10) -> Dict[str, Any]:
    try:
        raw_config = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw_config, dict):
            raise ValueError("not an object")
        if not isinstance(raw_config.get("roots", []), list) or not all(isinstance(item, str) for item in raw_config.get("roots", [])):
            raise ValueError("invalid roots")
        config, config_state = raw_config, {"path": str(config_path), "available": True, "readable": True, "state": "ok"}
    except (OSError, ValueError, json.JSONDecodeError):
        config, config_state = {}, {"path": str(config_path), "available": config_path.is_file(), "readable": False, "state": "invalid"}

    database_path = Path(str(config.get("database", DEFAULT_DATABASE)))
    events_path = events_path or Path(str(config.get("event_log", DEFAULT_EVENTS)))
    feedback_path = feedback_path or Path(str(config.get("feedback_log", DEFAULT_FEEDBACK)))
    roots = [str(item) for item in config.get("roots", []) if isinstance(item, str)]
    events, event_state = _read_events(events_path)
    feedback_state = _read_feedback(feedback_path)
    database = _read_database(database_path)
    freshness = _freshness(database_path, roots, database)

    decisions = dict(sorted(Counter(str(event.get("decision")) for event in events).items()))
    candidate_counts = Counter(str(item.get("name")) for event in events for item in event.get("candidates", []))
    candidates = [{"name": name, "count": count} for name, count in sorted(candidate_counts.items(), key=lambda item: (-item[1], item[0]))[: max(1, top_candidates)]]
    explicit_count = sum(1 for event in events if event.get("decision") == "suggest" and len(event.get("candidates", [])) == 1 and isinstance(event["candidates"][0].get("score"), (int, float)) and event["candidates"][0]["score"] == 1.0)
    degraded = (
        config_state["state"] != "ok" or event_state["state"] != "ok"
        or feedback_state["state"] != "ok" or database["state"] != "ok"
        or bool(freshness.get("refresh_needed"))
    )
    return {
        "schema_version": 1, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "degraded" if degraded else "healthy", "configuration": config_state,
        "events": event_state, "decisions": decisions, "latency_ms": _latency(events),
        "top_candidates": candidates,
        "explicit_invocations": {"count": explicit_count, "basis": "single score-1.0 suggestion"},
        "feedback": feedback_state, "freshness": freshness, "database": database,
        "privacy_mode": "hash_only", "network_mode": "local_only_disabled",
    }


def _safe_inline(value: Any) -> str:
    text = str(value).replace("`", "'").replace("|", "/")
    return "".join(character for character in text if character.isprintable()).strip() or "N/A"


def render_markdown(report_data: Dict[str, Any]) -> str:
    latency = report_data["latency_ms"]
    lines = [
        "# Skill Router Health Report", "",
        f"- Status: `{report_data['status']}`", f"- Generated UTC: `{report_data['generated_utc']}`", "",
        "## Event counts and decisions", f"- Event counts: {report_data['events']['count']}",
        f"- Decision counts: {json.dumps(report_data['decisions'], sort_keys=True)}", "",
        "## Latency", f"- Count: {latency['count']}", f"- Mean: {latency['mean_ms']} ms",
        f"- Min/p50/p90/p95/max: {latency['min_ms']} / {latency['p50_ms']} / {latency['p90_ms']} / {latency['p95_ms']} / {latency['max_ms']} ms", "",
        "## Top candidates",
    ]
    lines.extend([f"- `{_safe_inline(item['name'])}`: {item['count']}" for item in report_data["top_candidates"]] or ["- None"])
    explicit = report_data["explicit_invocations"]
    lines.extend(["", "## Explicit invocations", f"- Count: {explicit['count']} ({explicit['basis']})", ""])
    feedback_data = report_data["feedback"]
    lines.extend(["## Feedback", f"- Record counts: {feedback_data['record_count']}",
                  f"- Verdict counts: {json.dumps(feedback_data.get('verdict_counts', {}), sort_keys=True)}", ""])
    freshness = report_data["freshness"]
    lines.extend(["## Freshness", f"- Refresh needed: {freshness.get('refresh_needed')}",
                  f"- Reason: `{_safe_inline(freshness.get('reason', 'unknown'))}`", ""])
    database = report_data["database"]
    lines.extend(["## Database integrity", f"- State: `{database['state']}`",
                  f"- Quick check: `{_safe_inline(database['integrity'])}`",
                  f"- Indexed skills / manifest rows: {database.get('skill_count', 'N/A')} / {database.get('manifest_count', 'N/A')}", ""])
    lines.extend(["## Privacy", "- Mode: `hash_only`", "- Raw prompts and secrets: excluded", "", "## Network", "- Mode: `local_only_disabled`", "- Remote telemetry: disabled", ""])
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG); parser.add_argument("--events-path", type=Path); parser.add_argument("--feedback-path", type=Path)
    parser.add_argument("--top-candidates", type=int, default=10); parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    result = build_report(config_path=args.config, events_path=args.events_path, feedback_path=args.feedback_path, top_candidates=args.top_candidates)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render_markdown(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
