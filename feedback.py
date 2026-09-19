#!/usr/bin/env python3
"""Private hash-only feedback storage and evaluation for Skill Router."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
HERE = Path(__file__).resolve().parent
DEFAULT_EVENTS_PATH = HERE / "events.jsonl"
DEFAULT_FEEDBACK_PATH = HERE / "feedback.jsonl"
VERDICTS = frozenset(("useful", "wrong", "superseded"))
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
def event_identity(event: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(event).encode("utf-8")).hexdigest()
def _read_jsonl(path: Path, kind: str) -> List[Dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"{kind} file does not exist: {path}")
    if path.is_symlink():
        raise ValueError(f"{kind} file must not be a symlink: {path}")
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError(f"{kind} file has an unterminated final JSON record")
    records: List[Dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw.splitlines(), 1):
        if not raw_line.strip():
            raise ValueError(f"{kind} line {line_number} is empty")
        try:
            value = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"malformed {kind} JSON at line {line_number}: {error}") from error
        if not isinstance(value, dict):
            raise ValueError(f"{kind} line {line_number} is not a JSON object")
        if "prompt" in value or "raw_prompt" in value:
            raise ValueError(f"{kind} line {line_number} contains a raw prompt field")
        records.append(value)
    return records
def _validated_event(event: Dict[str, Any], line_number: int) -> Dict[str, Any]:
    decision = event.get("decision")
    duration = event.get("duration_ms")
    candidates = event.get("candidates")
    valid = isinstance(event.get("prompt_sha256"), str) and bool(HASH_RE.fullmatch(str(event["prompt_sha256"])))
    valid = valid and isinstance(candidates, list) and all(isinstance(i, dict) and isinstance(i.get("name"), str) for i in candidates)
    invalid = decision not in ("suggest", "abstain") or isinstance(duration, bool) or not isinstance(duration, int) or duration < 0
    if not valid or invalid or (decision == "suggest") != bool(candidates):
        raise ValueError(f"invalid event record at line {line_number}")
    return event
def load_events(path: Path = DEFAULT_EVENTS_PATH) -> List[Dict[str, Any]]:
    events = [_validated_event(e, i) for i, e in enumerate(_read_jsonl(path, "events"), 1)]
    identities = [event_identity(event) for event in events]
    if len(identities) != len(set(identities)):
        raise ValueError("events contain duplicate stable identities")
    return events
def _validated_feedback(entry: Dict[str, Any], line_number: int) -> Dict[str, Any]:
    hashes = ("event_id", "prompt_sha256")
    if entry.get("schema_version") != 1:
        raise ValueError(f"invalid feedback record at line {line_number}")
    if entry.get("verdict") not in VERDICTS:
        raise ValueError(f"invalid verdict at line {line_number}")
    if not isinstance(entry.get("event_id"), str) or HASH_RE.fullmatch(str(entry["event_id"])) is None:
        raise ValueError(f"invalid event_id at feedback line {line_number}")
    if not isinstance(entry.get("prompt_sha256"), str) or HASH_RE.fullmatch(str(entry["prompt_sha256"])) is None:
        raise ValueError(f"invalid prompt_sha256 at feedback line {line_number}")
    if not isinstance(entry.get("timestamp"), str) or not entry["timestamp"]:
        raise ValueError(f"invalid timestamp at feedback line {line_number}")
    if any(entry.get(f) is not None and not isinstance(entry.get(f), str) for f in ("better_skill", "notes")):
        raise ValueError(f"invalid optional feedback field at line {line_number}")
    return entry
def load_feedback(path: Path = DEFAULT_FEEDBACK_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        if path.is_symlink():
            raise ValueError(f"feedback file must not be a symlink: {path}")
        return list()
    records = _read_jsonl(path, "feedback")
    return [_validated_feedback(e, i) for i, e in enumerate(records, 1)]
def _append_feedback(path: Path, entry: Dict[str, Any]) -> None:
    encoded = (_canonical_json(entry) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        if os.write(descriptor, encoded) != len(encoded):
            raise OSError("incomplete feedback append")
    finally:
        os.close(descriptor)
def record_feedback(
    event_id: str, verdict: str, *, better_skill: Optional[str] = None, notes: Optional[str] = None,
    events_path: Path = DEFAULT_EVENTS_PATH, feedback_path: Path = DEFAULT_FEEDBACK_PATH
) -> Dict[str, Any]:
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of: {', '.join(sorted(VERDICTS))}")
    if better_skill is not None and (not better_skill.strip() or "\n" in better_skill):
        raise ValueError("better_skill must be non-empty single-line text")
    if notes is not None and ("\x00" in notes or "\r" in notes):
        raise ValueError("notes must not contain control line breaks")
    events = load_events(events_path)
    matches = [event for event in events if event_identity(event) == event_id]
    if len(matches) != 1:
        raise ValueError(f"event_id must identify exactly one event (matched {len(matches)})")
    event = matches[0]
    if feedback_path.exists():
        load_feedback(feedback_path)
    entry = {
        "schema_version": 1,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event_id": event_id,
        "prompt_sha256": event["prompt_sha256"],
        "verdict": verdict,
    }
    entry.update({key: value for key, value in (("better_skill", better_skill), ("notes", notes)) if value is not None})
    _append_feedback(feedback_path, entry)
    return dict(entry)
def _frequency(values: Iterable[str]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))
def evaluate(
    *, events_path: Path = DEFAULT_EVENTS_PATH, feedback_path: Path = DEFAULT_FEEDBACK_PATH
) -> Dict[str, Any]:
    events = load_events(events_path)
    feedback = load_feedback(feedback_path)
    latest = {str(entry["event_id"]): entry for entry in feedback}
    matched = [
        (event, latest[event_identity(event)])
        for event in events
        if event_identity(event) in latest
    ]
    top1_matches = [(event, entry) for event, entry in matched if event["candidates"]]
    verdict_counts = {verdict: 0 for verdict in sorted(VERDICTS)}
    verdict_counts.update(_frequency(entry["verdict"] for _event, entry in top1_matches))
    correction_targets = [
        str(entry["better_skill"])
        for _event, entry in top1_matches
        if entry["verdict"] in ("wrong", "superseded") and entry.get("better_skill")
    ]
    suggested = [event for event in events if event["decision"] == "suggest"]
    abstained = [event for event in events if event["decision"] == "abstain"]
    rated = len(top1_matches)
    return {
        "event_count": len(events),
        "feedback_record_count": len(feedback),
        "matched_feedback_count": len(matched),
        "unmatched_feedback_count": len(latest) - len(matched),
        "top1_usefulness": {
            "rated": rated,
            "useful": verdict_counts["useful"],
            "wrong": verdict_counts["wrong"],
            "superseded": verdict_counts["superseded"],
            "useful_rate": round(verdict_counts["useful"] / rated, 6) if rated else None,
        },
        "corrections": {"count": len(correction_targets), "targets": _frequency(correction_targets)},
        "candidate_frequency": _frequency(
            str(item["name"]) for event in suggested for item in event["candidates"]
        ),
        "latency_ms": {
            "count": len(events),
            "mean_ms": round(sum(int(event["duration_ms"]) for event in events) / len(events), 3)
            if events else None,
        },
        "abstentions": {
            "count": len(abstained),
            "rate": round(len(abstained) / len(events), 6) if events else None,
        },
    }
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    record = commands.add_parser("record", help="append verdict feedback for one event")
    review = commands.add_parser("evaluate", help="print a JSON evaluation report")
    for command in (record, review):
        command.add_argument("--events-path", type=Path, default=DEFAULT_EVENTS_PATH)
        command.add_argument("--feedback-path", type=Path, default=DEFAULT_FEEDBACK_PATH)
    record.add_argument("--event-id", required=True)
    record.add_argument("--verdict", choices=sorted(VERDICTS), required=True)
    for argument in ("--better-skill", "--notes"):
        record.add_argument(argument)
    return parser
def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "record":
        result = record_feedback(
            args.event_id, args.verdict, better_skill=args.better_skill, notes=args.notes, events_path=args.events_path,
            feedback_path=args.feedback_path,
        )
    else:
        result = evaluate(events_path=args.events_path, feedback_path=args.feedback_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"feedback: {error}", file=sys.stderr)
        raise SystemExit(2)
