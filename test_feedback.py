#!/usr/bin/env python3
"""Tests for private Skill Router feedback and evaluation."""
from __future__ import annotations
import io
import json
import tempfile
import unittest
import feedback
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict
HERE = Path(__file__).resolve().parent
def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(i, sort_keys=True) + "\n" for i in records), encoding="utf-8")
class FeedbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = feedback
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.events = self.root / "events.jsonl"
        self.feedback = self.root / "feedback.jsonl"
        def event(hash_: str, second: int, duration: int, decision: str, names: list[str]):
            candidates = [{"name": n, "path": f"/{n}", "score": .8, "matched": ["x"]} for n in names]
            return {"timestamp": f"2026-09-19T00:00:0{second}Z", "event": "skill_router", "prompt_sha256": hash_, "duration_ms": duration, "decision": decision, "candidates": candidates}
        self.records = [
            event("a" * 64, 1, 12, "suggest", ["alpha", "beta"]),
            event("b" * 64, 2, 20, "suggest", ["beta"]),
            event("c" * 64, 3, 8, "abstain", []),
        ]
        write_jsonl(self.events, self.records)
    def tearDown(self) -> None:
        self.temp.cleanup()
    def record(self, event_id: str, verdict: str, **kwargs: Any) -> Dict[str, Any]:
        return self.module.record_feedback(event_id, verdict, events_path=self.events, feedback_path=self.feedback, **kwargs)
    def test_malformed_existing_store_fails_loudly_before_append(self) -> None:
        event_id = self.module.event_identity(self.records[0])
        with self.assertRaisesRegex(ValueError, "verdict must"):
            self.record(event_id, "excellent")
        with self.assertRaisesRegex(ValueError, "exactly one event"):
            self.record("d" * 64, "wrong")
        self.feedback.write_text("{bad json\n", encoding="utf-8")
        before = self.feedback.read_bytes()
        with self.assertRaisesRegex(ValueError, "malformed feedback JSON"):
            self.record(event_id, "useful")
        self.assertEqual(before, self.feedback.read_bytes())
    def test_append_only_storage_and_latest_join_report(self) -> None:
        first_id = self.module.event_identity(self.records[0])
        second_id = self.module.event_identity(self.records[1])
        first = self.record(first_id, "useful")
        self.assertEqual("a" * 64, first["prompt_sha256"])
        self.assertEqual(0o600, self.feedback.stat().st_mode & 0o777)
        prefix = self.feedback.read_bytes()
        self.record(first_id, "superseded", better_skill="beta", notes="correction")
        self.record(second_id, "wrong", better_skill="gamma")
        self.assertTrue(self.feedback.read_bytes().startswith(prefix))
        self.assertEqual(3, len(self.feedback.read_text(encoding="utf-8").splitlines()))
        with self.feedback.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "schema_version": 1, "timestamp": "2026-09-19T00:00:04Z",
                "event_id": "e" * 64, "prompt_sha256": "f" * 64, "verdict": "useful",
            }, sort_keys=True) + "\n")
        report = self.module.evaluate(
            events_path=self.events, feedback_path=self.feedback
        )
        self.assertEqual((3, 4, 2, 1), (
            report["event_count"], report["feedback_record_count"],
            report["matched_feedback_count"], report["unmatched_feedback_count"],
        ))
        self.assertEqual(
            {"rated": 2, "useful": 0, "wrong": 1, "superseded": 1, "useful_rate": 0.0},
            report["top1_usefulness"],
        )
        self.assertEqual({"beta": 1, "gamma": 1}, report["corrections"]["targets"])
        self.assertEqual({"alpha": 1, "beta": 2}, report["candidate_frequency"])
        self.assertEqual(13.333, report["latency_ms"]["mean_ms"])
        self.assertEqual({"count": 1, "rate": 0.333333}, report["abstentions"])
        self.assertNotIn("prompt_sha256", json.dumps(report))
    def test_real_events_fixture_and_cli_commands(self) -> None:
        real_events = HERE / "fixtures" / "events.jsonl"
        event_id = self.module.event_identity(
            json.loads(real_events.read_text(encoding="utf-8").splitlines()[0])
        )
        common = ["--events-path", str(real_events), "--feedback-path", str(self.feedback)]
        output = io.StringIO()
        with redirect_stdout(output):
            self.module.main(
                ["record", "--event-id", event_id, "--verdict", "useful", "--notes", "integration fixture", *common]
            )
        output = io.StringIO()
        with redirect_stdout(output):
            self.module.main(["evaluate", *common])
        report = json.loads(output.getvalue())
        self.assertGreater(report["event_count"], 0)
        self.assertEqual(1, report["matched_feedback_count"])
        self.assertEqual(1, report["top1_usefulness"]["useful"])
        self.assertEqual(0o600, self.feedback.stat().st_mode & 0o777)
if __name__ == "__main__":
    unittest.main()
