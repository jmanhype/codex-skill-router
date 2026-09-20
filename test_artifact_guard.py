#!/usr/bin/env python3
"""Hard-TDD and real-filesystem tests for the global artifact guard."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import threading
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional

import artifact_guard as guard


HERE = Path(__file__).resolve().parent
CATALOG = guard.OracleCatalog.load(HERE / "design")
EXPECTED_STABLE_IDS = frozenset(
    {
        "ARTF-166f17", "ARTF-8526af", "ARTF-4519af",
        "STAG-8af0e4", "STAG-cfb530", "STAG-910d99",
        "HASH-08bd15", "HASH-f9bb6c",
        "LEAS-07f187", "LEAS-60ee49", "LEAS-941578", "LEAS-d276b5",
        "AUDI-39c46c", "AUDI-da531b",
        "TXN-0ce397", "TXN-305eaa", "TXN-3958f3", "TXN-55eac5",
        "TXN-07ee49", "TXN-78feea", "TXN-896a3d", "TXN-92359e",
        "TXN-bbca31", "TXN-c06d44", "TXN-c5c4ad", "TXN-d8cb41",
        "TXN-f69729", "TXN-f9d923", "TXN-fe36a0", "TXN-5fd1c7",
    }
)


class OracleTransitionTests(unittest.TestCase):
    def test_catalog_covers_exactly_all_30_stable_ids(self) -> None:
        observed = {row.stable_id for row in CATALOG.transitions}
        self.assertEqual(EXPECTED_STABLE_IDS, observed)
        self.assertEqual(30, len(CATALOG.transitions))

    def _record(self, transition: guard.OracleTransition) -> guard.StateRecord:
        if transition.machine == "artifact":
            return guard.ArtifactRecord("artifact")
        if transition.machine == "stagedArtifact":
            return guard.StagedArtifactRecord("stage")
        if transition.machine == "hashExpectation":
            return guard.HashExpectationRecord("hash")
        if transition.machine == "lease":
            return guard.LeaseRecord("lease")
        if transition.machine == "auditRecord":
            return guard.AuditRecord("audit")
        return guard.ArtifactTransactionRecord("transaction", HERE)

    def _action(self, transition: guard.OracleTransition) -> None:
        record = self.current
        if transition.action == "bindStageIdentity":
            record.stage_id = "stage-bound"
        elif transition.action == "bindPostHash":
            record.post_sha256 = "post-bound"
        elif transition.action == "bindRestoredPreHash":
            record.restored_sha256 = "restored-bound"
        elif transition.action == "bindInstalledHash":
            record.installed_sha256 = "installed-bound"

    def run_transition(self, transition: guard.OracleTransition) -> None:
        self.current = self._record(transition)
        self.current.state = transition.source
        dispatched = CATALOG.dispatch(self.current, transition.event, self._action)
        self.assertEqual(transition.stable_id, dispatched.stable_id)
        self.assertEqual(transition.target, self.current.state)


for _transition in CATALOG.transitions:
    def _oracle_test(self: OracleTransitionTests, row=_transition) -> None:
        self.assertIn(row.stable_id, EXPECTED_STABLE_IDS)
        with self.subTest(stable_id=row.stable_id, test_id=row.test_id):
            self.run_transition(row)

    _oracle_test.__name__ = f"test_oracle_{_transition.stable_id.replace('-', '_')}"
    _oracle_test.__doc__ = f"Cover generated oracle stable id {_transition.stable_id}."
    setattr(OracleTransitionTests, _oracle_test.__name__, _oracle_test)


class GuardIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.source_root = root / "source"
        self.live_root = root / "live"
        self.control_root = root / "control"
        self.source_root.mkdir()
        self.live_root.mkdir()
        self.alpha_source = self.source_root / "alpha.py"
        self.beta_source = self.source_root / "beta.py"
        self.alpha_source.write_bytes(b"alpha-new\n")
        self.beta_source.write_bytes(b"beta-new\n")
        self.alpha_target = self.live_root / "alpha.py"
        self.beta_target = self.live_root / "nested" / "beta.py"
        self.alpha_target.write_bytes(b"alpha-old\n")
        self.beta_target.parent.mkdir(parents=True)
        self.beta_target.write_bytes(b"beta-old\n")
        os.chmod(self.alpha_target, 0o640)
        os.chmod(self.beta_target, 0o600)
        self.alpha_hash = guard.sha256_path(self.alpha_source)
        self.beta_hash = guard.sha256_path(self.beta_source)
        self.alpha_pre = guard.sha256_path(self.alpha_target)
        self.beta_pre = guard.sha256_path(self.beta_target)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def declarations(self, stale: bool = False):
        beta_pre = "0" * 64 if stale else self.beta_pre
        return [
            guard.ArtifactDeclaration(self.alpha_source, Path("alpha.py"), self.alpha_hash, self.alpha_pre, 0o644),
            guard.ArtifactDeclaration(self.beta_source, Path("nested/beta.py"), self.beta_hash, beta_pre, 0o644),
        ]

    def new_guard(self, stale: bool = False) -> guard.ArtifactGuard:
        return guard.ArtifactGuard(self.live_root, self.source_root, self.control_root)

    def test_stage_is_immutable_content_addressed_and_source_hash_bound(self) -> None:
        transaction = guard.ArtifactGuard(self.live_root, self.source_root, self.control_root)
        transaction.propose(self.declarations())
        transaction.stage()
        stage = transaction.stages[transaction.live_root / "alpha.py"]
        self.assertEqual("Sealed", stage.state)
        self.assertEqual(self.alpha_hash, stage.content_sha256)
        self.assertEqual(self.alpha_hash, stage.stage_path.name)
        self.assertEqual(0, stat.S_IMODE(stage.stage_path.stat().st_mode) & 0o222)
        os.chmod(self.alpha_source, 0o644)
        self.alpha_source.write_bytes(b"changed-after-seal\n")
        transaction.stage_store.verify(stage.stage_path, self.alpha_hash)
        self.assertEqual(
            self.alpha_hash,
            transaction.artifacts[transaction.live_root / "alpha.py"].source_sha256,
        )

    def test_source_hash_mismatch_rejects_before_staging_or_live_mutation(self) -> None:
        before = guard.sha256_path(self.alpha_target)
        transaction = guard.ArtifactGuard(self.live_root, self.source_root, self.control_root)
        transaction.propose(self.declarations())
        with self.assertRaises(guard.HashMismatchError) as raised:
            transaction.stage_store.seal(self.alpha_source, "1" * 64)
        self.assertEqual("STALE_HASH", raised.exception.code)
        rejected = self.new_guard()
        rejected.propose(
            [
                guard.ArtifactDeclaration(
                    self.alpha_source, Path("alpha.py"), "1" * 64, self.alpha_pre
                )
            ]
        )
        with self.assertRaises(guard.HashMismatchError):
            rejected.stage()
        self.assertEqual("Rejected", rejected.transaction.state)
        records = rejected.audit_log.records()
        self.assertEqual(1, len(records))
        self.assertEqual("STALE_HASH", records[0]["rejectionCode"])
        self.assertEqual(before, guard.sha256_path(self.alpha_target))

    def test_parent_symlink_cannot_escape_live_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="csr-escape-") as escape_name:
            escape = Path(escape_name)
            outside = escape / "outside.bin"
            outside.write_bytes(b"outside")
            linked = self.live_root / "linked"
            linked.symlink_to(escape, target_is_directory=True)
            declaration = guard.ArtifactDeclaration(
                self.alpha_source, Path("linked/outside.bin"), self.alpha_hash
            )
            with self.assertRaises(guard.InvalidDeclarationError):
                self.new_guard().propose([declaration])

    def test_successful_commit_installs_complete_set_and_audits_all_hashes(self) -> None:
        transaction = self.new_guard()
        transaction.propose(self.declarations())
        transaction.stage()
        transaction.acquire_lease()
        result = transaction.commit()
        self.assertEqual("committed", result.outcome)
        self.assertEqual(b"alpha-new\n", self.alpha_target.read_bytes())
        self.assertEqual(b"beta-new\n", self.beta_target.read_bytes())
        self.assertEqual(0o640, stat.S_IMODE(self.alpha_target.stat().st_mode))
        self.assertEqual(0o600, stat.S_IMODE(self.beta_target.stat().st_mode))
        records = transaction.audit_log.records()
        self.assertEqual(1, len(records))
        hashes = records[0]["hashes"]
        self.assertEqual(self.alpha_hash, hashes["source:alpha.py"])
        self.assertEqual(self.alpha_pre, hashes["pre:alpha.py"])
        self.assertEqual(self.alpha_hash, hashes["post:alpha.py"])
        self.assertTrue(all(stage.state == "Committed" and stage.installed_sha256 == stage.content_sha256 for stage in transaction.stages.values()))
        self.assertEqual(0, len(list((self.control_root / "leases").glob("*.json"))))

    def test_stage_oserror_uses_stable_rejection_code(self) -> None:
        transaction = self.new_guard(); os.chmod(self.alpha_source, 0)
        try:
            with self.assertRaises(guard.StageFailureError) as raised: transaction.propose(self.declarations()); transaction.stage()
        finally: os.chmod(self.alpha_source, 0o644)
        self.assertEqual("STAGE_FAILED", raised.exception.code); self.assertEqual("STAGE_FAILED", transaction.transaction.rejection_code)
        records = transaction.audit_log.records(); self.assertEqual(1, len(records)); self.assertEqual("STAGE_FAILED", records[0]["rejectionCode"])

    def test_stale_pre_hash_releases_lease_and_does_not_mutate_target(self) -> None:
        transaction = self.new_guard(stale=True)
        transaction.propose(self.declarations(stale=True))
        transaction.stage()
        with self.assertRaises(guard.HashMismatchError):
            transaction.acquire_lease()
        self.assertEqual("Rejected", transaction.transaction.state)
        self.assertEqual("STALE_HASH", transaction.transaction.rejection_code)
        self.assertEqual(b"alpha-old\n", self.alpha_target.read_bytes())
        self.assertEqual(0, len(list((self.control_root / "leases").glob("*.json"))))
        records = transaction.audit_log.records()
        self.assertEqual(1, len(records))
        self.assertEqual("STALE_HASH", records[0]["rejectionCode"])

    def test_exclusive_lease_has_exactly_one_concurrent_winner(self) -> None:
        guards = []
        for _ in range(4):
            transaction = guard.ArtifactGuard(self.live_root, self.source_root, self.control_root)
            transaction.propose(self.declarations())
            transaction.stage()
            guards.append(transaction)
        barrier = threading.Barrier(len(guards))
        outcomes: List[Optional[guard.ArtifactTransactionRecord]] = [None] * len(guards)
        errors: List[Optional[BaseException]] = [None] * len(guards)

        def compete(index: int) -> None:
            barrier.wait()
            try:
                outcomes[index] = guards[index].acquire_lease()
            except BaseException as error:
                errors[index] = error

        threads = [threading.Thread(target=compete, args=(index,)) for index in range(len(guards))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(1, sum(value is not None for value in outcomes))
        self.assertEqual(3, sum(isinstance(value, guard.LeaseDeniedError) for value in errors))
        winner = next(guards[index] for index, value in enumerate(outcomes) if value is not None)
        self.assertEqual("Leased", winner.transaction.state)
        for loser_index, error in enumerate(errors):
            if isinstance(error, guard.LeaseDeniedError):
                self.assertEqual("Rejected", guards[loser_index].transaction.state)
                for stage in guards[loser_index].stages.values():
                    self.assertEqual("Rejected", stage.state)
                    guard.StageStore(self.control_root / "stages").verify(stage.stage_path, stage.content_sha256)
        self.assertEqual(1, len(list((self.control_root / "leases").glob("*.json"))))

    def test_prepared_replacement_failure_restores_exact_pre_bytes_and_modes(self) -> None:
        transaction = self.new_guard()
        transaction.propose(self.declarations())
        transaction.stage()
        transaction.acquire_lease()
        os.chmod(self.beta_target.parent, 0o500)
        try:
            result = transaction.commit()
            self.assertEqual("rolled_back", result.outcome)
            self.assertEqual("COMMIT_FAILED", result.rejection_code)
            self.assertEqual("RolledBack", transaction.transaction.state)
            self.assertEqual(b"alpha-old\n", self.alpha_target.read_bytes())
            self.assertEqual(b"beta-old\n", self.beta_target.read_bytes())
            self.assertEqual(0o640, stat.S_IMODE(self.alpha_target.stat().st_mode))
            self.assertEqual(0o600, stat.S_IMODE(self.beta_target.stat().st_mode))
        finally:
            os.chmod(self.beta_target.parent, 0o700)

    def test_audit_append_failure_rolls_back_complete_declared_set(self) -> None:
        transaction = self.new_guard()
        audit_path = self.control_root / "audit.jsonl"
        audit_path.mkdir(parents=True)
        transaction.propose(self.declarations())
        transaction.stage()
        transaction.acquire_lease()
        result = transaction.commit()
        self.assertEqual("rolled_back", result.outcome)
        self.assertEqual("AUDIT_FAILED", result.rejection_code)
        self.assertEqual(b"alpha-old\n", self.alpha_target.read_bytes())
        self.assertEqual(b"beta-old\n", self.beta_target.read_bytes())
        self.assertTrue(audit_path.is_dir())

    def test_partial_capture_failure_releases_lease_without_mutating_targets(self) -> None:
        transaction = self.new_guard(); transaction.propose(self.declarations()); transaction.stage(); transaction.acquire_lease(); os.chmod(self.beta_target, 0)
        try: result = transaction.commit()
        finally: os.chmod(self.beta_target, 0o600)
        self.assertEqual("rolled_back", result.outcome); self.assertEqual("RolledBack", transaction.transaction.state)
        self.assertEqual(b"alpha-old\n", self.alpha_target.read_bytes()); self.assertEqual(b"beta-old\n", self.beta_target.read_bytes())
        self.assertEqual(0, len(list((self.control_root / "leases").glob("*.json"))))

    def test_malformed_audit_json_is_audit_failure_and_rolls_back(self) -> None:
        transaction = self.new_guard(); transaction.propose(self.declarations()); transaction.stage(); transaction.acquire_lease()
        transaction.audit_log.path.write_text("{not-json\n", encoding="utf-8")
        with self.assertRaises(guard.AuditAppendError): transaction.audit_log.append("audit-probe", "rejected", {})
        result = transaction.commit(); self.assertEqual("AUDIT_FAILED", result.rejection_code); self.assertEqual(b"alpha-old\n", self.alpha_target.read_bytes()); self.assertEqual(b"beta-old\n", self.beta_target.read_bytes())

    def test_parent_symlink_swapped_after_validation_cannot_escape_live_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="csr-post-escape-") as escape_name:
            transaction = self.new_guard(); transaction.propose(self.declarations()); transaction.stage(); transaction.acquire_lease()
            escape = Path(escape_name) / "escape"; real = self.live_root / "real-nested"; os.rename(self.beta_target.parent, real); escape.mkdir(); (self.beta_target.parent).symlink_to(escape, target_is_directory=True)
            result = transaction.commit()
            self.assertEqual("COMMIT_FAILED", result.rejection_code); self.assertEqual(b"alpha-old\n", self.alpha_target.read_bytes()); self.assertEqual([], list(escape.iterdir())); self.assertEqual(0, len(list((self.control_root / "leases").glob("*.json"))))

    def test_expired_acquired_partial_replacement_recovers_exact_prestate(self) -> None:
        transaction = self.new_guard(); transaction.propose(self.declarations()); transaction.stage(); transaction.acquire_lease(); transaction.oracle.dispatch(transaction.transaction, "commit"); transaction._capture_pre_state(); transaction._write_journal()
        with self.assertRaises(KeyboardInterrupt): transaction._install_all(crash_after=1)
        self.assertEqual(b"alpha-new\n", self.alpha_target.read_bytes()); self.assertEqual(b"beta-old\n", self.beta_target.read_bytes())
        lease_files = list((self.control_root / "leases").glob("*.json")); self.assertEqual(1, len(lease_files)); self.assertEqual("Acquired", json.loads(lease_files[0].read_text())["state"])
        recovered = guard.ArtifactGuard.recover_after_crash(self.live_root, self.source_root, self.control_root, now=float(transaction.lease.expires_at) + 1)
        self.assertEqual("Recovered", recovered.transaction.state); self.assertEqual(b"alpha-old\n", self.alpha_target.read_bytes()); self.assertEqual(b"beta-old\n", self.beta_target.read_bytes()); self.assertEqual(0, len(list((self.control_root / "leases").glob("*.json"))))
        self.assertIn("LEASE_ORPHAN_RECOVERED", [record["outcome"] for record in recovered.audit_log.records()])

    def test_expired_acquired_preaction_lease_is_audited_and_cleared(self) -> None:
        transaction = self.new_guard(); transaction.propose(self.declarations()); transaction.stage(); transaction.acquire_lease()
        with self.assertRaises(guard.RecoveryError): guard.ArtifactGuard.recover_after_crash(self.live_root, self.source_root, self.control_root, now=float(transaction.lease.expires_at) + 1)
        self.assertEqual(0, len(list((self.control_root / "leases").glob("*.json")))); self.assertEqual("LEASE_ORPHAN_RECOVERED", transaction.audit_log.records()[-1]["outcome"])

    def test_bounded_crash_recovery_reverifies_pre_hashes_and_audits(self) -> None:
        transaction = self.new_guard()
        transaction.propose(self.declarations())
        transaction.stage()
        transaction.acquire_lease()
        transaction.mark_crash()
        future = float("inf")
        transaction.recover(now=future)
        self.assertEqual("Recovered", transaction.transaction.state)
        self.assertEqual(0, len(list((self.control_root / "leases").glob("*.json"))))
        events = transaction.audit_log.records()
        self.assertEqual(1, len(events))
        self.assertEqual("LEASE_ORPHAN_RECOVERED", events[0]["outcome"])
        self.assertNotIn("ownerToken", events[0])

    def test_unbounded_recovery_fails_and_stale_recovery_never_promotes(self) -> None:
        transaction = self.new_guard()
        transaction.propose(self.declarations())
        transaction.stage()
        transaction.acquire_lease()
        transaction.mark_crash()
        with self.assertRaises(guard.RecoveryError):
            transaction.recover(now=0)
        self.assertEqual("Rejected", transaction.transaction.state); self.assertEqual("UNSAFE_RECOVERY", transaction.audit_log.records()[-1]["rejectionCode"])
        self.assertEqual(1, len(list((self.control_root / "leases").glob("*.json"))))

        stale = guard.ArtifactGuard(
            self.live_root, self.source_root, self.control_root.parent / "control-stale"
        )
        stale.propose(self.declarations())
        stale.stage()
        stale.acquire_lease()
        stale.mark_crash()
        self.beta_target.write_bytes(b"externally-changed\n")
        with self.assertRaises(guard.RecoveryError):
            stale.recover(now=float("inf"))
        self.assertEqual(b"externally-changed\n", self.beta_target.read_bytes())

    def test_verify_only_cli_performs_zero_writes(self) -> None:
        root = Path(self.temp.name) / "cli-live"
        target = root / "config.json"
        target.parent.mkdir()
        target.write_bytes(b"read-only baseline\n")
        baseline = Path(self.temp.name) / "baseline.sha256"
        digest = guard.sha256_path(target)
        baseline.write_text(f"{digest}  {target}\n", encoding="utf-8")
        before = self.snapshot(root)
        completed = subprocess.run(
            [
                "/usr/bin/python3",
                str(HERE / "artifact_guard.py"),
                "--root",
                str(root),
                "--baseline",
                str(baseline),
                "--verify-only",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(0, payload["writes"])
        self.assertTrue(payload["all_matched"])
        self.assertEqual(digest, payload["eligible"][0]["observed_sha256"])
        self.assertEqual(before, self.snapshot(root))

    @staticmethod
    def snapshot(root: Path) -> Dict[str, tuple]:
        result: Dict[str, tuple] = {}
        for path in sorted(root.rglob("*")):
            if path.is_file():
                result[str(path.relative_to(root))] = (
                    guard.sha256_path(path),
                    stat.S_IMODE(path.stat().st_mode),
                    path.stat().st_size,
                )
        return result


if __name__ == "__main__":
    unittest.main()
