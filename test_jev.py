#!/usr/bin/env python3
"""Fake-transport tests for consent-gated Jev skill reranking."""

from __future__ import annotations

import importlib.util, io, json, sys, tempfile, unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import jev


class BrokenResponse:
    def read(self, _: int) -> bytes:
        raise OSError("connection reset while reading")


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class JevUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.before = [
            {"name": "alpha-widget-local", "path": "/private/alpha", "score": 0.72,
             "matched": ["alpha", "widget", "diagnostic"], "term_overlap": 0.6,
             "local_only": "never transmitted"},
            {"name": "alpha-widget-remote", "path": "/private/beta", "score": 0.70,
             "matched": ["alpha", "widget", "triage"], "term_overlap": 0.6,
             "local_only": "also private"},
        ]
        self.candidates = [dict(item) for item in self.before]
        self.config = {
            "jev_reranking": {
                "enabled": True,
                "timeout_seconds": 0.75,
                "prompt_summary_chars": 32,
            }
        }

    def test_successful_retry_and_bounded_payload(self) -> None:
        requests: List[Dict[str, Any]] = []

        def fake(payload: Dict[str, Any], key: str, timeout: float) -> io.BytesIO:
            requests.append({"payload": payload, "key": key, "timeout": timeout})
            if len(requests) == 1:
                raise TimeoutError("first attempt")
            return io.BytesIO(json.dumps({"ranking": ["c1", "c0"]}).encode())

        result = jev.rerank(
            "Alpha widget diagnostic SECRET_SUFFIX_MUST_NOT_LEAVE",
            self.candidates,
            self.config,
            api_key="secret-key",
            transport=fake,
        )
        self.assertEqual(2, len(requests))
        self.assertLessEqual(requests[0]["timeout"], 0.25)
        self.assertEqual("secret-key", requests[0]["key"])
        self.assertEqual(
            ["alpha-widget-remote", "alpha-widget-local"],
            [item["name"] for item in result],
        )
        payload = requests[0]["payload"]
        self.assertEqual(32, len(payload["prompt_summary"]))
        self.assertNotIn("SECRET_SUFFIX_MUST_NOT_LEAVE", json.dumps(payload))
        serialized = json.dumps(payload)
        self.assertNotIn("/private/", serialized)
        self.assertNotIn("local_only", serialized)
        self.assertEqual(self.before, self.candidates)
        self.assertCountEqual(self.before, result)

    def test_disabled_and_missing_key_never_transport(self) -> None:
        def fail(_: Dict[str, Any], __: str, ___: float) -> io.BytesIO:
            raise AssertionError("transport must not run")

        disabled = {"jev_reranking": {"enabled": False}}
        self.assertEqual(self.before, jev.rerank("x", self.candidates, disabled, transport=fail))
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(self.before, jev.rerank("x", self.candidates, self.config, transport=fail))

    def test_timeout_malformed_and_none_fall_back(self) -> None:
        cases: List[Any] = [
            OSError("network unavailable"),
            io.BytesIO(b"{malformed"),
            BrokenResponse(),
            io.BytesIO(json.dumps({"ranking": ["none"]}).encode()),
        ]
        expected: List[Any] = [2, 1, 1, 1]
        for response, calls in zip(cases, expected):
            with self.subTest(response=response):
                count = [0]

                def fake(_: Dict[str, Any], __: str, ___: float) -> Any:
                    count[0] += 1
                    if isinstance(response, Exception):
                        raise response
                    return response

                result = jev.rerank(
                    "x", self.candidates, self.config, api_key="key", transport=fake
                )
                self.assertEqual(calls, count[0])
                self.assertEqual(self.before, result)

class JevIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.skills = cls.root / "skills"
        for name in ("alpha-widget-one", "alpha-widget-two"):
            directory = cls.skills / name
            directory.mkdir(parents=True)
            directory.joinpath("SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Debug Alpha widget diagnostics.\n---\n"
                "# Alpha Widget Diagnostics\n", encoding="utf-8"
            )
        cls.index = load_module("codex_skill_index", HERE / "index_skills.py")
        cls.hook = load_module("codex_skill_hook", HERE / "hook.py")
        cls.database = cls.root / "skills.sqlite3"
        records = cls.index.skill_records([str(cls.skills)])
        cls.index.build_database(cls.database, records, [str(cls.skills)])
        cls.config = {"database": str(cls.database), "event_log": str(cls.root / "events.jsonl"),
                      "roots": [str(cls.skills)], "max_candidates": 2, "minimum_confidence": 0.5,
                      "minimum_term_overlap": 0.34, "candidate_window": 0.18,
                      "jev_reranking": {"enabled": True, "prompt_summary_chars": 32}}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_fake_transport_end_to_end_through_ambiguous_fts(self) -> None:
        requests: List[Dict[str, Any]] = []

        def fake_urlopen(request: Any, timeout: float) -> io.BytesIO:
            body = json.loads(request.data.decode("utf-8"))
            requests.append({"url": request.full_url, "headers": dict(request.header_items()),
                             "timeout": timeout, "body": body})
            return io.BytesIO(json.dumps({"ranking": ["c1", "c0"]}).encode())

        with mock.patch.dict(
            "os.environ", {"TYPESAFE_API_KEY": "integration-key"}, clear=True
        ), mock.patch.object(self.hook.jev, "urlopen", fake_urlopen):
            _prompt, candidates = self.hook.handle_payload(
                {"prompt": "Alpha widget diagnostics SECRET_SUFFIX"}, self.config
            )

        self.assertEqual((1, jev.JEV_ENDPOINT), (len(requests), requests[0]["url"])); self.assertEqual("Bearer integration-key", requests[0]["headers"]["Authorization"])
        self.assertEqual(2, len(candidates)); self.assertNotEqual("alpha-widget-one", candidates[0]["name"])
        body = json.dumps(requests[0]["body"]); self.assertFalse("SECRET_SUFFIX" in body or "path" in body)


if __name__ == "__main__":
    unittest.main()
