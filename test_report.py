#!/usr/bin/env python3
"""Tests for the local Skill Router health and quality report."""
from __future__ import annotations

import io, json, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import report


def event(name: str, duration: int, decision: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {"timestamp": f"2026-09-19T00:00:0{len(name) % 10}Z", "event": "skill_router", "prompt_sha256": name * 64, "duration_ms": duration, "decision": decision, "candidates": candidates}


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.events = self.root / "events.jsonl"
        self.feedback = self.root / "feedback.jsonl"
        alpha = {"name": "alpha", "path": "/skills/alpha", "score": 1.0, "matched": ["alpha"]}
        beta = {"name": "beta", "path": "/skills/beta", "score": 0.8, "matched": ["alpha"]}
        records = [event("a", 12, "suggest", [alpha, beta]), event("b", 20, "suggest", [{**beta, "score": 1.0, "matched": ["beta"]}]), event("c", 8, "abstain", [])]
        self.events.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in records), encoding="utf-8")
        feedback = [{"schema_version": 1, "timestamp": "2026-09-19T00:00:04Z", "event_id": "a" * 64, "prompt_sha256": "a" * 64, "verdict": "useful"}, {"schema_version": 1, "timestamp": "2026-09-19T00:00:05Z", "event_id": "b" * 64, "prompt_sha256": "b" * 64, "verdict": "wrong", "better_skill": "alpha"}]
        self.feedback.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in feedback), encoding="utf-8")
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({"database": str(self.root / "missing.sqlite3"), "event_log": str(self.events), "feedback_log": str(self.feedback), "roots": [str(self.root / "skills")]}), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_aggregates_and_privacy_mode(self) -> None:
        result = report.build_report(config_path=self.config, events_path=self.events, feedback_path=self.feedback)
        self.assertEqual(3, result["events"]["count"])
        self.assertEqual({"suggest": 2, "abstain": 1}, result["decisions"])
        self.assertEqual({"count": 3, "mean_ms": 13.333, "min_ms": 8, "p50_ms": 12, "p90_ms": 20, "p95_ms": 20, "max_ms": 20}, result["latency_ms"])
        self.assertEqual([{"name": "beta", "count": 2}, {"name": "alpha", "count": 1}], result["top_candidates"])
        self.assertEqual(1, result["explicit_invocations"]["count"])
        self.assertEqual(2, result["feedback"]["record_count"])
        self.assertEqual({"wrong": 1, "useful": 1}, result["feedback"]["verdict_counts"])
        self.assertEqual("hash_only", result["privacy_mode"])
        self.assertEqual("local_only_disabled", result["network_mode"])
        self.assertNotIn("prompt_sha256", json.dumps(result))
        self.assertNotIn("a" * 64, json.dumps(result))

    def test_missing_and_malformed_artifacts_degrade_without_crashing(self) -> None:
        missing = report.build_report(config_path=self.config, events_path=self.root / "missing.jsonl", feedback_path=self.root / "missing.jsonl")
        self.assertEqual("degraded", missing["status"])
        self.assertFalse(missing["events"]["available"])
        self.assertEqual(0, missing["events"]["count"])
        self.assertEqual("missing", missing["database"]["state"])
        self.assertEqual("database_missing", missing["freshness"]["reason"])
        self.assertFalse(missing["feedback"]["available"])
        self.events.write_text("{bad\n", encoding="utf-8")
        invalid = report.build_report(config_path=self.config, events_path=self.events, feedback_path=self.feedback)
        self.assertEqual("degraded", invalid["status"])
        self.assertFalse(invalid["events"]["readable"])
        self.assertIsNone(invalid["events"]["count"])
        self.assertEqual("invalid", invalid["events"]["state"])

    def test_real_artifacts_support_markdown_and_json_cli_formats(self) -> None:
        json_output = io.StringIO()
        with redirect_stdout(json_output):
            self.assertEqual(0, report.main(["--format", "json"]))
        machine = json.loads(json_output.getvalue())
        self.assertGreater(machine["events"]["count"], 0)
        self.assertIn("ok", machine["database"]["integrity"])
        markdown_output = io.StringIO()
        with redirect_stdout(markdown_output):
            self.assertEqual(0, report.main(["--format", "markdown"]))
        markdown = markdown_output.getvalue()
        for heading in ("Event counts", "Decision counts", "Latency", "Top candidates", "Explicit invocations", "Feedback", "Freshness", "Database integrity", "Privacy", "Network"):
            self.assertIn(heading, markdown)
        self.assertNotIn("prompt_sha256", markdown)


if __name__ == "__main__":
    unittest.main()
