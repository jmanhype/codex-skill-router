#!/usr/bin/env python3
"""Regression tests for standalone Paivot governance."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class GovernanceTests(unittest.TestCase):
    def test_repository_local_paivot_adapters_are_configured(self) -> None:
        config = (ROOT / ".paivot" / "config.yaml").read_text(encoding="utf-8")
        active = "".join(line for line in config.splitlines(keepends=True) if not line.lstrip().startswith("#"))
        self.assertIn("adapter: nd", active)
        self.assertIn("vault: .vault", active)
        self.assertIn("adapter: vlt", active)
        self.assertNotIn("adapter: linear", active)
        self.assertNotIn("adapter: confluence", active)

    def test_nd_uses_git_common_dir_vault(self) -> None:
        shared = (ROOT / ".vault" / ".nd-shared.yaml").read_text(encoding="utf-8")
        self.assertIn("mode: git_common_dir", shared)
        self.assertIn("path: paivot/nd-vault", shared)

    def test_live_vault_runtime_state_is_not_tracked(self) -> None:
        ignore = (ROOT / ".vault" / ".gitignore").read_text(encoding="utf-8")
        for path in ("issues/", ".nd.yaml", ".vlt.lock", ".dispatcher-state.json"):
            self.assertIn(path, ignore)
        self.assertFalse((ROOT / ".vault" / "issues").exists())

    def test_readme_documents_standalone_governance(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Standalone Paivot governance", readme)
        self.assertIn("repository-local", readme)
        self.assertIn("wangp-dspy", readme)


if __name__ == "__main__":
    unittest.main()
