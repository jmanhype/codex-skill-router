#!/usr/bin/env python3
"""Tests for the local Codex skill indexer and UserPromptSubmit hook."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock


HERE = Path(__file__).resolve().parent
SKIP_LIVE_INDEX = os.environ.get("CI") == "true"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index_module = load_module("codex_skill_index", HERE / "index_skills.py")
        cls.hook_module = load_module("codex_skill_hook", HERE / "hook.py")
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        cls.root = root

        alpha = root / "skills" / "alpha-widget-debugging"
        calendar = root / "skills" / "calendar-planning"
        alpha.mkdir(parents=True)
        calendar.mkdir(parents=True)
        (alpha / "SKILL.md").write_text(
            """---
name: alpha-widget-debugging
description: |
  Debug Alpha widget failures when the frontend shows no data.
---

# Alpha Widget Debugging

Use for Alpha widget diagnostics and frontend empty-state failures.
""",
            encoding="utf-8",
        )
        (calendar / "SKILL.md").write_text(
            """---
name: "calendar-planning"
description: Plan calendar events and meetings.
---

# Calendar Planning
""",
            encoding="utf-8",
        )

        cls.database = root / "skills.sqlite3"
        cls.event_log = root / "events.jsonl"
        cls.config: Dict[str, Any] = {
            "database": str(cls.database),
            "event_log": str(cls.event_log),
            "max_candidates": 3,
            "minimum_confidence": 0.5,
            "minimum_term_overlap": 0.34,
            "candidate_window": 0.18,
            "roots": [str(root / "skills")],
        }
        (root / "config.json").write_text(
            json.dumps(cls.config, indent=2), encoding="utf-8"
        )
        cls.config_path = root / "config.json"

        records = cls.index_module.skill_records([str(root / "skills")])
        cls.index_module.build_database(cls.database, records, cls.config["roots"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_index_builds_fts_and_strips_quoted_name(self) -> None:
        connection = sqlite3.connect(f"file:{self.database}?mode=ro", uri=True)
        try:
            count = connection.execute("SELECT count(*) FROM skills").fetchone()[0]
            names = [
                row[0]
                for row in connection.execute("SELECT name FROM skills ORDER BY name")
            ]
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(2, count)
        self.assertEqual(
            ["alpha-widget-debugging", "calendar-planning"], names
        )
        self.assertEqual("ok", integrity)
        self.assertEqual(0o600, self.database.stat().st_mode & 0o777)


    def test_relevant_prompt_selects_expected_skill(self) -> None:
        _prompt, candidates = self.hook_module.handle_payload(
            {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Debug the Alpha widget frontend showing no data.",
            },
            self.config,
        )
        self.assertTrue(candidates)
        self.assertEqual("alpha-widget-debugging", candidates[0]["name"])
        self.assertGreaterEqual(candidates[0]["score"], 0.5)

    def test_explicit_invocation_syntax_resolves_requested_fixture_skill(self) -> None:
        prompts = [
            "$alpha-widget-debugging",
            "Please use skill alpha-widget-debugging now.",
            "Please use the alpha-widget-debugging skill now.",
            "Invoke skill alpha-widget-debugging for this task.",
            "Load skill alpha-widget-debugging for this task.",
            "skill: alpha-widget-debugging",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                _prompt, candidates = self.hook_module.handle_payload(
                    {"hook_event_name": "UserPromptSubmit", "prompt": prompt},
                    self.config,
                )
                self.assertEqual(1, len(candidates), candidates)
                self.assertEqual("alpha-widget-debugging", candidates[0]["name"])
                self.assertEqual(
                    str(
                        (self.root / "skills" / "alpha-widget-debugging" / "SKILL.md").resolve()
                    ),
                    candidates[0]["path"],
                )
                self.assertEqual(1.0, candidates[0]["score"])

    @unittest.skipIf(SKIP_LIVE_INDEX, "requires the operator's installed live skill index")
    def test_natural_language_goal_request_is_not_explicit_invocation(self) -> None:
        config = self.hook_module.load_config(self.hook_module.CONFIG_PATH)
        connection = sqlite3.connect(f"file:{config['database']}?mode=ro", uri=True)
        try:
            resolved = self.hook_module.resolve_explicit_invocation(
                connection, "Please define a goal for this project."
            )
        finally:
            connection.close()
        self.assertIsNone(resolved)

    @unittest.skipIf(SKIP_LIVE_INDEX, "requires the operator's installed live skill index")
    def test_real_index_explicit_invocation_returns_exact_skill(self) -> None:
        config = self.hook_module.load_config(self.hook_module.CONFIG_PATH)
        _prompt, candidates = self.hook_module.handle_payload(
            {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Use skill supabase-rls-frontend-debugging please.",
            },
            config,
        )
        self.assertEqual(1, len(candidates), candidates)
        self.assertEqual("supabase-rls-frontend-debugging", candidates[0]["name"])
        self.assertEqual(
            "/Users/speed/.agents/skills/supabase-rls-frontend-debugging/SKILL.md",
            candidates[0]["path"],
        )
        self.assertEqual(1.0, candidates[0]["score"])

    def test_unknown_explicit_invocation_falls_back_without_error(self) -> None:
        _prompt, candidates = self.hook_module.handle_payload(
            {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "use skill definitely-not-an-installed-skill",
            },
            self.config,
        )
        self.assertEqual([], candidates)

    @unittest.skipIf(SKIP_LIVE_INDEX, "requires the operator's installed live skill index")
    def test_live_meta_language_prefers_specific_current_index_skill(self) -> None:
        config = self.hook_module.load_config(self.hook_module.CONFIG_PATH)
        self.assertTrue(Path(str(config["database"])).is_file())
        prompt = (
            "Live hook verification: Why does my Supabase frontend show empty "
            "rows when the API returns data? First quote the exact Skill Router "
            "advisory context injected into this turn, or say "
            "NO_SKILL_ROUTER_CONTEXT if none was injected. Then answer the "
            "technical question in two sentences."
        )
        _prompt, candidates = self.hook_module.handle_payload(
            {"hook_event_name": "UserPromptSubmit", "prompt": prompt},
            config,
        )
        names = [item["name"] for item in candidates]
        self.assertIn("supabase", names)
        self.assertIn("supabase-rls-frontend-debugging", names)
        self.assertLess(
            names.index("supabase-rls-frontend-debugging"),
            names.index("supabase"),
        )

    @unittest.skipIf(SKIP_LIVE_INDEX, "requires the operator's installed live skill index")
    def test_short_domain_prompt_still_returns_current_index_domain_skill(self) -> None:
        config = self.hook_module.load_config(self.hook_module.CONFIG_PATH)
        self.assertTrue(Path(str(config["database"])).is_file())
        _prompt, candidates = self.hook_module.handle_payload(
            {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Use Supabase for a database query.",
            },
            config,
        )
        self.assertTrue(
            [item for item in candidates if "supabase" in item["name"].casefold()]
        )

    def test_hook_output_shape_is_compact_and_advisory(self) -> None:
        _prompt, candidates = self.hook_module.handle_payload(
            {"prompt": "Alpha widget diagnostics"}, self.config
        )
        context = self.hook_module.format_context(candidates)
        self.assertIn("Skill Router advisory", context)
        self.assertIn("alpha-widget-debugging", context)
        self.assertIn("only if it matches", context)
        self.assertLessEqual(len(context), 2000)

    def test_conversational_prompt_abstains(self) -> None:
        _prompt, candidates = self.hook_module.handle_payload(
            {"hook_event_name": "UserPromptSubmit", "prompt": "nice"}, self.config
        )
        self.assertEqual([], candidates)

    def test_unrecoverable_missing_database_fails_open_by_abstaining(self) -> None:
        config = dict(self.config)
        config["database"] = str(self.root / "missing.sqlite3")
        with mock.patch.object(
            self.index_module,
            "ensure_fresh_index",
            side_effect=RuntimeError("simulated refresh failure"),
        ):
            _prompt, candidates = self.hook_module.handle_payload(
                {"prompt": "Alpha widget diagnostics"}, config
            )
        self.assertEqual([], candidates)

    def test_event_log_contains_hash_but_not_raw_prompt(self) -> None:
        prompt = "Secret Alpha widget diagnostic prompt 7f31a"
        self.hook_module.log_event(
            self.event_log, prompt, 12, "suggest", [{"name": "x", "path": "/x", "score": 1, "matched": ["alpha"]}]
        )
        raw = self.event_log.read_text(encoding="utf-8")
        self.assertNotIn(prompt, raw)
        self.assertNotIn("Secret Alpha", raw)
        event = json.loads(raw.splitlines()[-1])
        self.assertEqual(64, len(event["prompt_sha256"]))
        self.assertEqual("suggest", event["decision"])

    def test_malformed_stdin_returns_empty_json_and_exits_zero(self) -> None:
        original_config = self.hook_module.CONFIG_PATH
        original_stdin = sys.stdin
        try:
            self.hook_module.CONFIG_PATH = self.config_path
            sys.stdin = io.StringIO("{bad json")
            output = io.StringIO()
            with redirect_stdout(output):
                result = self.hook_module.main()
        finally:
            self.hook_module.CONFIG_PATH = original_config
            sys.stdin = original_stdin
        self.assertEqual(0, result)
        self.assertEqual({}, json.loads(output.getvalue()))


class IndexFreshnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index_module = load_module("codex_skill_index", HERE / "index_skills.py")
        cls.hook_module = load_module("codex_skill_hook", HERE / "hook.py")
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.skills = cls.root / "skills"
        cls.overlap = cls.root / "overlap"
        primary = cls.skills / "orbital-teapot-calibration"
        duplicate = cls.overlap / "duplicate-orbital-skill"
        primary.mkdir(parents=True)
        duplicate.mkdir(parents=True)
        (primary / "SKILL.md").write_text(
            """---
name: orbital-teapot-calibration
description: Calibrate orbital teapot alignment.
---

# Orbital Teapot Calibration
""",
            encoding="utf-8",
        )
        (duplicate / "SKILL.md").write_text(
            """---
name: orbital-teapot-calibration
description: Duplicate logical name that must not enter the FTS index.
---
""",
            encoding="utf-8",
        )
        cls.database = cls.root / "skills.sqlite3"
        cls.config: Dict[str, Any] = {
            "database": str(cls.database),
            "event_log": str(cls.root / "events.jsonl"),
            "roots": [str(cls.skills), str(cls.overlap)],
            "max_candidates": 3,
            "minimum_confidence": 0.5,
            "minimum_term_overlap": 0.34,
            "candidate_window": 0.18,
        }
        records = cls.index_module.skill_records(cls.config["roots"])
        cls.index_module.build_database(cls.database, records, cls.config["roots"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_automatic_refresh_reindexes_changed_and_new_skills(self) -> None:
        primary = self.skills / "orbital-teapot-calibration" / "SKILL.md"
        primary.write_text(
            """---
name: orbital-teapot-calibration
description: Diagnose gyroscopic lattice drift.
---

# Gyroscopic Lattice Drift
""",
            encoding="utf-8",
        )
        new_skill = self.skills / "probabilistic-kite-routing"
        new_skill.mkdir()
        (new_skill / "SKILL.md").write_text(
            """---
name: probabilistic-kite-routing
description: Route probabilistic kites through wind corridors.
---

# Probabilistic Kite Routing
""",
            encoding="utf-8",
        )

        for prompt in (
            "Diagnose gyroscopic lattice drift.",
            "Route probabilistic kites through wind corridors.",
        ):
            with self.subTest(prompt=prompt):
                _prompt, candidates = self.hook_module.handle_payload(
                    {"hook_event_name": "UserPromptSubmit", "prompt": prompt},
                    self.config,
                )
                self.assertTrue(candidates)

        connection = sqlite3.connect(f"file:{self.database}?mode=ro", uri=True)
        try:
            names = [
                row[0]
                for row in connection.execute("SELECT name FROM skills ORDER BY name")
            ]
            included = connection.execute(
                "SELECT count(*) FROM skill_manifest WHERE included = 1"
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(2, len(names))
        self.assertEqual(len(set(names)), len(names))
        self.assertEqual(len(names), included)
        self.assertFalse(
            self.index_module.index_freshness(
                self.database, self.config["roots"]
            )["refresh_needed"]
        )
        self.assertEqual(0o600, self.database.stat().st_mode & 0o777)

    def test_corrupt_and_missing_database_are_rebuilt_safely(self) -> None:
        prompt = "Diagnose gyroscopic lattice drift."
        self.database.write_bytes(b"not a sqlite database")
        _prompt, candidates = self.hook_module.handle_payload(
            {"hook_event_name": "UserPromptSubmit", "prompt": prompt},
            self.config,
        )
        self.assertTrue(candidates)

        self.database.unlink()
        _prompt, candidates = self.hook_module.handle_payload(
            {"hook_event_name": "UserPromptSubmit", "prompt": prompt},
            self.config,
        )
        self.assertTrue(candidates)
        self.assertEqual(0o600, self.database.stat().st_mode & 0o777)

    def test_refresh_failure_fails_open_and_never_uses_network(self) -> None:
        with mock.patch.object(
            self.index_module,
            "ensure_fresh_index",
            return_value={"refresh_needed": False, "refresh_failed": True},
        ), mock.patch("socket.socket", side_effect=AssertionError("network use")):
            _prompt, candidates = self.hook_module.handle_payload(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "Diagnose gyroscopic lattice drift.",
                },
                self.config,
            )
        self.assertTrue(candidates)

    def test_unchanged_sources_do_not_rebuild_or_rehash(self) -> None:
        with mock.patch.object(self.index_module, "build_database") as build:
            _prompt, candidates = self.hook_module.handle_payload(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "Calibrate orbital teapot alignment.",
                },
                self.config,
            )
        self.assertTrue(candidates)
        build.assert_not_called()

        primary = self.skills / "orbital-teapot-calibration" / "SKILL.md"
        old_stat = primary.stat()
        os.utime(
            primary,
            ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 1_000_000_000),
        )
        status = self.index_module.ensure_fresh_index(self.config)
        self.assertFalse(status["refresh_needed"])
        self.assertTrue(status["manifest_updated"])

        with mock.patch.object(
            self.index_module,
            "file_fingerprint",
            side_effect=AssertionError("unchanged file was rehashed"),
        ):
            self.assertFalse(
                self.index_module.index_freshness(
                    self.database, self.config["roots"]
                )["refresh_needed"]
            )


if __name__ == "__main__":
    unittest.main()
