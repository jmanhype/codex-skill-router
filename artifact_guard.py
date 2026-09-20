"""Hash, lease, and atomic-replacement guard for machine-global artifacts."""; from __future__ import annotations; import argparse, fcntl, hashlib, json, os, re, stat, tempfile, threading, time, uuid; from dataclasses import dataclass; from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Protocol, Sequence, Tuple; SHA256_RE = re.compile('^[0-9a-f]{64}$'); MISSING_SHA256 = None
ORACLE_FILES = (('artifact', 'Artifact.oracle.md'), ('stagedArtifact', 'StagedArtifact.oracle.md'), ('hashExpectation', 'HashExpectation.oracle.md'), ('lease', 'Lease.oracle.md'), ('auditRecord', 'AuditRecord.oracle.md'), ('artifactTransaction', 'ArtifactTransaction.oracle.md'))
_AUDIT_LOCK = threading.Lock()
class ArtifactGuardError(RuntimeError):
    """Base error carrying a stable guard rejection code.""";     code = 'REJECTED'
class InvalidDeclarationError(ArtifactGuardError):
    code = 'INVALID_DECLARATION'
class HashMismatchError(ArtifactGuardError):
    code = 'STALE_HASH'
    def __init__(self, subject: str, expected: Optional[str], observed: Optional[str]) -> None:
        super().__init__(f'{subject} hash mismatch: expected={expected} observed={observed}');         self.subject = subject;         self.expected = expected;         self.observed = observed
class InvalidTransitionError(ArtifactGuardError):
    code = 'INVALID_TRANSITION'
class LeaseDeniedError(ArtifactGuardError):
    code = 'LEASE_DENIED'
    def __init__(self, message: str, owner_fingerprint: Optional[str]=None) -> None:
        super().__init__(message);         self.owner_fingerprint = owner_fingerprint
class AuditAppendError(ArtifactGuardError):
    code = 'AUDIT_FAILED'
class TransactionCommitError(ArtifactGuardError):
    code = 'COMMIT_FAILED'
class RollbackError(ArtifactGuardError):
    code = 'ROLLBACK_FAILED'
class RecoveryError(ArtifactGuardError):
    code = 'UNSAFE_RECOVERY'
def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda : handle.read(1048576), b''): digest.update(block)
    return digest.hexdigest()
def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
@dataclass(frozen=True)
class OracleTransition:
    machine: str;     stable_id: str;     test_id: str;     source: str;     event: str;     target: str;     action: str;     guard: Optional[str] = None
def parse_oracle_markdown(path: Path, machine: str) -> List[OracleTransition]:
    rows: List[OracleTransition] = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not re.match('^\\|\\s*T-[^|]+\\|', line): continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) < 7: raise ValueError(f'invalid oracle row in {path}: {line}')
        (test_id, stable_id, source, trigger, guard, target, action) = cells[:7]
        if not test_id.startswith('T-') or not re.match('^[A-Z]+-[a-f0-9]{6}$', stable_id): continue
        if not trigger.startswith('on:'): raise ValueError(f'oracle trigger is not an event: {line}')
        rows.append(OracleTransition(machine, stable_id, test_id, source, trigger[3:], target, action, None if guard == '-' else guard))
    if not rows: raise ValueError(f'no oracle transitions found in {path}')
    return rows
class OracleCatalog:
    def __init__(self, transitions: Sequence[OracleTransition]) -> None:
        stable_ids = [row.stable_id for row in transitions]
        if len(stable_ids) != len(set(stable_ids)): raise ValueError('duplicate oracle stable id')
        if len(transitions) != 30: raise ValueError(f'expected 30 oracle transitions, found {len(transitions)}')
        self.transitions = tuple(transitions);         self.by_id = {row.stable_id: row for row in transitions}
    @classmethod
    def load(cls, design_dir: Path) -> 'OracleCatalog':
        return cls([row for (machine, filename) in ORACLE_FILES for row in parse_oracle_markdown(design_dir / 'machines' / filename, machine)])
    def dispatch(self, record: 'StateRecord', event: str, action: Optional[Callable[[OracleTransition], None]]=None) -> OracleTransition:
        matches = [row for row in self.transitions if row.machine == record.kind and row.source == record.state and (row.event == event)]
        if len(matches) != 1: raise InvalidTransitionError(f'{record.kind}/{record.state} does not permit event {event}')
        transition = matches[0];         record.state = transition.target
        if action is not None: action(transition)
        return transition
@dataclass
class ArtifactRecord:
    kind = 'artifact';     artifact_id: str;     state: str = 'Selected';     source_path: Optional[Path] = None;     target_path: Optional[Path] = None;     stage_id: Optional[str] = None;     source_sha256: Optional[str] = None;     pre_sha256: Optional[str] = None
    post_sha256: Optional[str] = None;     restored_sha256: Optional[str] = None
@dataclass
class StagedArtifactRecord:
    kind = 'stagedArtifact';     stage_id: str;     state: str = 'Sealed';     content_sha256: Optional[str] = None;     stage_path: Optional[Path] = None;     installed_sha256: Optional[str] = None
@dataclass
class HashExpectationRecord:
    kind = 'hashExpectation';     expectation_id: str;     state: str = 'Proposed';     expected_sha256: Optional[str] = None;     observed_sha256: Optional[str] = None
@dataclass
class LeaseRecord:
    kind = 'lease';     lease_id: str;     state: str = 'Free';     root_path: Optional[Path] = None;     owner_token: Optional[str] = None;     owner_fingerprint: Optional[str] = None;     expires_at: Optional[float] = None;     orphaned_at: Optional[float] = None
@dataclass
class AuditRecord:
    kind = 'auditRecord';     record_id: str;     state: str = 'Pending';     transaction_id: Optional[str] = None;     outcome: Optional[str] = None;     rejection_code: Optional[str] = None;     hashes: Tuple[Tuple[str, Optional[str], Optional[str]], ...] = ()
    append_error: Optional[str] = None
@dataclass
class ArtifactTransactionRecord:
    kind = 'artifactTransaction';     transaction_id: str;     root_path: Path;     state: str = 'Proposed';     artifact_ids: Tuple[str, ...] = ();     lease_id: Optional[str] = None;     rejection_code: Optional[str] = None;     started_at: Optional[float] = None
    ended_at: Optional[float] = None
class StateRecord(Protocol):
    kind: str;     state: str
@dataclass(frozen=True)
class ArtifactDeclaration:
    source_path: Path;     target_path: Path;     expected_source_sha256: str;     expected_pre_sha256: Optional[str] = None;     mode: int = 420
@dataclass(frozen=True)
class TransactionResult:
    transaction: ArtifactTransactionRecord;     outcome: str;     hashes: Dict[str, Optional[str]];     rejection_code: Optional[str] = None
class StageStore:
    """Content-addressed store whose sealed files are immutable evidence."""
    def __init__(self, root: Path) -> None:
        self.root = root
    def seal(self, source: Path, expected_sha256: str) -> StagedArtifactRecord:
        source = source.resolve(strict=True)
        if not source.is_file(): raise InvalidDeclarationError(f'source is not a regular file: {source}')
        if not SHA256_RE.fullmatch(expected_sha256): raise InvalidDeclarationError(f'invalid source SHA-256: {expected_sha256}')
        observed = sha256_path(source)
        if observed != expected_sha256: raise HashMismatchError('source', expected_sha256, observed)
        destination = self.root / observed[:2] / observed;         destination.parent.mkdir(parents=True, exist_ok=True, mode=448)
        if destination.exists(): self.verify(destination, observed)
        else: self._write_immutable(source, destination, observed)
        return StagedArtifactRecord(stage_id=f'stage-{observed}', content_sha256=observed, stage_path=destination)
    def _write_immutable(self, source: Path, destination: Path, expected: str) -> None:
        (fd, temporary_name) = tempfile.mkstemp(prefix='.stage-', dir=destination.parent);         temporary = Path(temporary_name)
        try:
            with source.open('rb') as source_handle, os.fdopen(fd, 'wb') as target_handle:
                for block in iter(lambda : source_handle.read(1024 * 1024), b''): target_handle.write(block)
                target_handle.flush();                 os.fsync(target_handle.fileno())
            observed = sha256_path(temporary)
            if observed != expected: raise HashMismatchError('staged', expected, observed)
            os.chmod(temporary, 292)
            try: os.link(temporary, destination)
            except FileExistsError: self.verify(destination, expected)
            _fsync_directory(destination.parent)
        finally: temporary.unlink(missing_ok=True)
    def verify(self, stage_path: Path, expected_sha256: str) -> None:
        metadata = stage_path.lstat()
        if not stat.S_ISREG(metadata.st_mode): raise InvalidDeclarationError(f'stage is not a regular file: {stage_path}')
        if metadata.st_mode & 146: raise InvalidDeclarationError(f'stage is mutable: {stage_path}')
        observed = sha256_path(stage_path)
        if observed != expected_sha256: raise HashMismatchError('stage', expected_sha256, observed)
class LeaseStore:
    """Exclusive per-live-root leases backed by O_CREAT|O_EXCL metadata."""
    def __init__(self, root: Path) -> None:
        self.root = root
    def _path(self, live_root: Path) -> Path:
        resolved = live_root.resolve(strict=True);         key = hashlib.sha256(str(resolved).encode('utf-8')).hexdigest();         return self.root / f'{key}.json'
    def acquire(self, live_root: Path, ttl_seconds: float, now: Optional[float]=None) -> LeaseRecord:
        if ttl_seconds <= 0: raise InvalidDeclarationError('lease TTL must be positive')
        current = time.time() if now is None else now;         lease_path = self._path(live_root);         lease_path.parent.mkdir(parents=True, exist_ok=True, mode=448);         lease_id = f'lease-{uuid.uuid4().hex}';         token = uuid.uuid4().hex
        payload = {'leaseId': lease_id, 'state': 'Acquired', 'rootPath': str(live_root.resolve(strict=True)), 'ownerToken': token, 'ownerFingerprint': hashlib.sha256(token.encode()).hexdigest(), 'expiresAt': current + ttl_seconds};         data = json.dumps(payload, sort_keys=True).encode('utf-8')
        try: fd = os.open(lease_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 384)
        except FileExistsError:
            try: existing = self._read(lease_path); detail, fingerprint = f'live root already has lease {existing.lease_id}', existing.owner_fingerprint
            except (OSError, ValueError, KeyError, json.JSONDecodeError): detail, fingerprint = 'live root lease metadata is reserved', None
            raise LeaseDeniedError(detail, fingerprint) from None
        try:
            with os.fdopen(fd, 'wb') as handle: handle.write(data) ; handle.flush() ; os.fsync(handle.fileno())
        except BaseException: lease_path.unlink(missing_ok=True) ; raise
        return LeaseRecord(lease_id=lease_id, state='Acquired', root_path=live_root.resolve(strict=True), owner_token=token, owner_fingerprint=payload['ownerFingerprint'], expires_at=payload['expiresAt'])
    def _read(self, path: Path) -> LeaseRecord:
        payload = json.loads(path.read_text(encoding='utf-8'));         state = payload.get('state')
        if state not in {'Acquired', 'Orphaned'}: raise RecoveryError(f'unknown persisted lease state: {state!r}')
        required = ('leaseId', 'ownerFingerprint', 'expiresAt')
        if any((not payload.get(name) for name in required)): raise RecoveryError('lease recovery evidence is incomplete')
        return LeaseRecord(lease_id=str(payload['leaseId']), state=str(state), root_path=Path(str(payload.get('rootPath', ''))), owner_token=payload.get('ownerToken'), owner_fingerprint=str(payload['ownerFingerprint']), expires_at=float(payload['expiresAt']), orphaned_at=payload.get('orphanedAt'))
    def release(self, lease: LeaseRecord) -> None:
        path = self._path(Path(lease.root_path or '/'));         existing = self._read(path)
        if existing.lease_id != lease.lease_id or existing.root_path != lease.root_path: raise LeaseDeniedError('lease owner identity does not match')
        if existing.owner_token != lease.owner_token: raise LeaseDeniedError('lease owner token does not match')
        path.unlink();         _fsync_directory(path.parent)
    def mark_orphaned(self, lease: LeaseRecord, now: Optional[float]=None) -> LeaseRecord:
        path = self._path(Path(lease.root_path or '/'));         existing = self._read(path)
        if existing.lease_id != lease.lease_id or existing.owner_token != lease.owner_token: raise LeaseDeniedError('only the recorded owner can mark a lease orphaned')
        current = time.time() if now is None else now;         payload = json.loads(path.read_text(encoding='utf-8'));         payload['state'] = 'Orphaned';         payload['orphanedAt'] = current;         (fd, temporary_name) = tempfile.mkstemp(prefix='.lease-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as handle: handle.write(json.dumps(payload, sort_keys=True).encode('utf-8')) ; handle.flush() ; os.fsync(handle.fileno())
            os.replace(temporary_name, path);             _fsync_directory(path.parent)
        finally: Path(temporary_name).unlink(missing_ok=True)
        existing.state = 'Orphaned';         existing.orphaned_at = current;         return existing
    def recover_orphan(self, live_root: Path, now: float, verifier: Callable[[], None], audit_writer: Callable[[Mapping[str, object]], None]) -> LeaseRecord:
        path = self._path(live_root);         lease = self._read(path)
        if lease.state != 'Orphaned' or lease.orphaned_at is None: raise RecoveryError('lease is not recorded as an orphan')
        if now < float(lease.expires_at): raise RecoveryError('lease expiry bound has not passed')
        verifier();         audit_writer({'outcome': 'LEASE_ORPHAN_RECOVERED', 'leaseId': lease.lease_id, 'ownerFingerprint': lease.owner_fingerprint, 'expiresAt': lease.expires_at});         path.unlink();         _fsync_directory(path.parent);         lease.state = 'Released'
        lease.owner_token = None;         return lease
class AuditLog:
    """Append-only JSONL terminal evidence."""
    def __init__(self, path: Path, dispatcher: OracleCatalog) -> None:
        self.path = path;         self.dispatcher = dispatcher;         self.last_terminal_append_error: Optional[str] = None
    def append(self, transaction_id: str, outcome: str, hashes: Mapping[str, Optional[str]], rejection_code: Optional[str]=None) -> AuditRecord:
        payload = {'transactionId': transaction_id, 'outcome': outcome, 'rejectionCode': rejection_code, 'hashes': dict(sorted(hashes.items()))};         identity = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        record = AuditRecord(record_id=hashlib.sha256(identity.encode('utf-8')).hexdigest(), transaction_id=transaction_id, outcome=outcome, rejection_code=rejection_code, hashes=tuple(hashes.items()))
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=448); fd = os.open(self.path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 384)
            with _AUDIT_LOCK, os.fdopen(fd, 'a+b') as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX); handle.seek(0); existing = {(item['transactionId'], item['outcome']) for item in (json.loads(line) for line in handle.read().decode('utf-8').splitlines() if line)}
                if (transaction_id, outcome) in existing: raise AuditAppendError('terminal audit outcome already exists')
                line = json.dumps({'recordId': record.record_id, **payload}, sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\n'; handle.seek(0, os.SEEK_END); handle.write(line); handle.flush(); os.fsync(handle.fileno())
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            self.dispatcher.dispatch(record, 'append')
        except OSError as error: rejected = AuditRecord(record_id=record.record_id, transaction_id=transaction_id, outcome=outcome, rejection_code=rejection_code, hashes=tuple(hashes.items()), append_error=str(error)) ; self.dispatcher.dispatch(rejected, 'rejectAppend') ; raise AuditAppendError(f'cannot append audit record: {error}') from error
        return record
    def append_event(self, event: Mapping[str, object]) -> Mapping[str, object]:
        line = json.dumps(event, sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\n'
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=448); fd = os.open(self.path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 384)
            with _AUDIT_LOCK, os.fdopen(fd, 'a+b') as handle: fcntl.flock(handle.fileno(), fcntl.LOCK_EX); handle.seek(0, os.SEEK_END); handle.write(line); handle.flush(); os.fsync(handle.fileno()); fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError as error: raise AuditAppendError(f'cannot append audit event: {error}') from error
        return event
    def records(self) -> List[Dict[str, object]]:
        if not self.path.exists(): rows: List[Dict[str, object]] = list()
        else: rows = [json.loads(line) for line in self.path.read_text(encoding='utf-8').splitlines() if line]
        return rows
@dataclass
class CapturedFile:
    target: Path;     existed: bool;     sha256: Optional[str];     mode: Optional[int];     evidence_path: Optional[Path] = None
class ArtifactGuard:
    """One declared-set transaction over a live root."""
    def __init__(self, live_root: Path, source_root: Path, control_root: Path, ttl_seconds: float=300.0, design_dir: Optional[Path]=None) -> None:
        self.live_root = live_root.resolve(strict=True);         self.source_root = source_root.resolve(strict=True);         self.control_root = control_root;         self.ttl_seconds = ttl_seconds;         search_dir = design_dir or Path(__file__).resolve().parent / 'design'
        self.oracle = OracleCatalog.load(search_dir);         self.stage_store = StageStore(control_root / 'stages');         self.lease_store = LeaseStore(control_root / 'leases');         self.audit_log = AuditLog(control_root / 'audit.jsonl', self.oracle)
        self.transaction = ArtifactTransactionRecord(transaction_id=f'txn-{uuid.uuid4().hex}', root_path=self.live_root, started_at=time.time());         self.declarations: Dict[Path, ArtifactDeclaration] = {};         self.artifacts: Dict[Path, ArtifactRecord] = {}
        self.stages: Dict[Path, StagedArtifactRecord] = {};         self.lease: Optional[LeaseRecord] = None;         self.pre_state: Dict[Path, CapturedFile] = {}
    def propose(self, declarations: Sequence[ArtifactDeclaration]) -> ArtifactTransactionRecord:
        if self.transaction.state != 'Proposed': raise InvalidTransitionError('transaction already proposed')
        targets: List[Path] = []
        for declaration in declarations:
            source = declaration.source_path.resolve(strict=True);             source.relative_to(self.source_root)
            if not source.is_file(): raise InvalidDeclarationError(f'source is not a file: {source}')
            target = Path(os.path.normpath(self.live_root / declaration.target_path)).resolve(strict=False)
            try: target.relative_to(self.live_root)
            except ValueError as error: raise InvalidDeclarationError(f'target escapes live root: {declaration.target_path}') from error
            if target == self.live_root or target in targets: raise InvalidDeclarationError(f'duplicate or invalid target: {target}')
            if target.is_symlink() or (os.path.lexists(target) and (not target.is_file())): raise InvalidDeclarationError(f'target must be a regular non-symlink file: {target}')
            if not SHA256_RE.fullmatch(declaration.expected_source_sha256): raise InvalidDeclarationError('invalid expected source SHA-256')
            if declaration.expected_pre_sha256 is not None and (not SHA256_RE.fullmatch(declaration.expected_pre_sha256)): raise InvalidDeclarationError('invalid expected pre SHA-256')
            targets.append(target);             self.declarations[target] = declaration;             self.artifacts[target] = ArtifactRecord(artifact_id=f'artifact-{len(targets)}', source_path=source, target_path=target)
        if not targets: raise InvalidDeclarationError('declared target set is empty')
        self.transaction.artifact_ids = tuple((item.artifact_id for item in self.artifacts.values()));         return self.transaction
    def stage(self) -> ArtifactTransactionRecord:
        if self.transaction.state != 'Proposed': raise InvalidTransitionError('sources are not open for staging')
        sealed: Dict[Path, StagedArtifactRecord] = {}
        try:
            for (target, declaration) in self.declarations.items(): stage = self.stage_store.seal(declaration.source_path, declaration.expected_source_sha256) ; sealed[target] = stage ; artifact = self.artifacts[target] ; self.oracle.dispatch(artifact, 'stage', lambda transition, artifact=artifact, stage=stage: self._bind_stage(artifact, stage))
        except (InvalidDeclarationError, HashMismatchError, OSError) as error: self.transaction.rejection_code = error.code ; expected = {'source:' + str(target.relative_to(self.live_root)): item.expected_source_sha256 for (target, item) in self.declarations.items()} ; self._reject(error.code, expected) ; raise
        self.stages = sealed;         self.oracle.dispatch(self.transaction, 'stage');         return self.transaction
    @staticmethod
    def _bind_stage(artifact: ArtifactRecord, stage: StagedArtifactRecord) -> None:
        artifact.stage_id = stage.stage_id;         artifact.source_sha256 = stage.content_sha256
    def _observed_pre(self, target: Path) -> Optional[str]:
        return sha256_path(target) if target.exists() else MISSING_SHA256
    def _verify_pre(self) -> Dict[str, Optional[str]]:
        observed = {str(target.relative_to(self.live_root)): self._observed_pre(target) for target in self.declarations}
        for (target, declaration) in self.declarations.items():
            key = str(target.relative_to(self.live_root))
            if observed[key] != declaration.expected_pre_sha256: raise HashMismatchError(f'live pre-state {key}', declaration.expected_pre_sha256, observed[key])
        return observed
    def acquire_lease(self) -> ArtifactTransactionRecord:
        if self.transaction.state != 'Staged': raise InvalidTransitionError('immutable stages are required before lease')
        for (target, stage) in self.stages.items(): self.stage_store.verify(Path(stage.stage_path), str(stage.content_sha256))
        try: self._verify_pre() ; lease = self.lease_store.acquire(self.live_root, self.ttl_seconds)
        except HashMismatchError as error: self._reject('STALE_HASH', self._all_hashes()) ; raise error
        except LeaseDeniedError as error: self.lease = None ; self.oracle.dispatch(self.transaction, 'leaseDenied') ; self.transaction.rejection_code = LeaseDeniedError.code ; self._mark_stages('reject') ; self._append_terminal('rejected', self._all_hashes(), LeaseDeniedError.code) ; raise error
        self.lease = lease;         self.oracle.dispatch(self.transaction, 'acquireLease');         self.transaction.lease_id = lease.lease_id
        try: self._verify_pre()
        except HashMismatchError as error: self.reject_stale_hash() ; raise error
        return self.transaction
    def reject_stale_hash(self) -> ArtifactTransactionRecord:
        if self.transaction.state != 'Leased' or self.lease is None: raise InvalidTransitionError('stale live hashes require an owned lease')
        hashes = self._all_hashes();         self.oracle.dispatch(self.transaction, 'staleHash');         self.transaction.rejection_code = HashMismatchError.code;         self._mark_stages('reject');         self._release_lease()
        self._append_terminal('rejected', hashes, HashMismatchError.code);         return self.transaction
    def _capture_pre_state(self) -> None:
        evidence = self.control_root / 'transactions' / self.transaction.transaction_id / 'pre';         evidence.mkdir(parents=True, exist_ok=True, mode=448);         manifest: List[Dict[str, object]] = []
        for (index, target) in enumerate(self.declarations):
            if target.exists():
                if not target.is_file(): raise InvalidDeclarationError(f'target is not a file: {target}')
                digest = sha256_path(target);                 evidence_path = evidence / f'{index:04d}.bin';                 evidence_path.write_bytes(target.read_bytes());                 os.chmod(evidence_path, 256)
                captured = CapturedFile(target, True, digest, stat.S_IMODE(target.stat().st_mode), evidence_path)
            else: captured = CapturedFile(target, False, None, None, None)
            self.pre_state[target] = captured;             manifest.append({'target': str(target.relative_to(self.live_root)), 'existed': captured.existed, 'sha256': captured.sha256, 'mode': captured.mode, 'evidencePath': str(captured.evidence_path) if captured.evidence_path else None})
        path = evidence / 'manifest.json';         path.write_text(json.dumps(manifest, sort_keys=True, indent=2), encoding='utf-8');         os.chmod(path, 256)
    def commit(self) -> TransactionResult:
        if self.transaction.state != 'Leased' or self.lease is None: raise InvalidTransitionError('commit requires an owned lease')
        self.oracle.dispatch(self.transaction, 'commit')
        try: self._capture_pre_state() ; self._verify_pre() ; pre_hashes = self._pre_hashes() ; self._install_all() ; post_hashes = self._post_hashes() ; all_hashes = self._merge_hashes(self._source_hashes(), pre_hashes, post_hashes) ; self._append_terminal('committed', all_hashes)
        except AuditAppendError as error: return self._failed_commit('auditFailed', AuditAppendError.code, error)
        except Exception as error: return self._failed_commit('commitFailed', TransactionCommitError.code, error)
        self.oracle.dispatch(self.transaction, 'commitAndAuditSucceeded');         self._mark_stages('markCommitted')
        for artifact in self.artifacts.values():
            if artifact.state != 'Committed': continue
            self.oracle.dispatch(artifact, 'markCommitted', lambda transition, artifact=artifact: None);             artifact.post_sha256 = sha256_path(Path(artifact.target_path))
        self._release_lease();         self.transaction.ended_at = time.time();         return TransactionResult(self.transaction, 'committed', self._all_hashes())
    def _install_all(self) -> None:
        replacements: List[Tuple[Path, Path, int]] = []
        try:
            for (target, declaration) in self.declarations.items():
                stage = self.stages[target];                 self.stage_store.verify(Path(stage.stage_path), str(stage.content_sha256));                 captured = self.pre_state[target];                 mode = int(captured.mode or declaration.mode)
                target.parent.mkdir(parents=True, exist_ok=True);                 (fd, temporary_name) = tempfile.mkstemp(prefix=f'.guard-{self.transaction.transaction_id}-', dir=target.parent);                 temporary = Path(temporary_name)
                with os.fdopen(fd, 'wb') as output, Path(stage.stage_path).open('rb') as source:
                    for block in iter(lambda : source.read(1024 * 1024), b''): output.write(block)
                    output.flush();                     os.fsync(output.fileno())
                os.chmod(temporary, mode);                 replacements.append((temporary, target, mode))
            for (temporary, target, _) in replacements: os.replace(temporary, target)
            for target in self.declarations:
                expected = self.stages[target].content_sha256;                 observed = sha256_path(target)
                if observed != expected: raise HashMismatchError('installed', str(expected), observed)
        finally:
            for (temporary, _, _) in replacements: temporary.unlink(missing_ok=True)
    def _failed_commit(self, event: str, code: str, cause: BaseException) -> TransactionResult:
        self.oracle.dispatch(self.transaction, event);         self.transaction.rejection_code = code;         self._mark_stages('reject')
        try: self._restore_pre_state()
        except Exception as rollback_error: self.oracle.dispatch(self.transaction, 'rollbackFailed') ; self._write_recovery_evidence(f'{code}; {rollback_error}') ; raise RollbackError(f'{code}; rollback failed: {rollback_error}') from rollback_error
        try: self._append_terminal('rolled_back', self._all_hashes(), code)
        except AuditAppendError as error: self.audit_log.last_terminal_append_error = str(error)
        self.oracle.dispatch(self.transaction, 'rollbackSucceeded');         self._release_lease();         self.transaction.ended_at = time.time();         return TransactionResult(self.transaction, 'rolled_back', self._all_hashes(), code)
    def _restore_pre_state(self) -> None:
        for target in reversed(list(self.declarations)):
            captured = self.pre_state.get(target)
            if captured is None: raise RollbackError(f'missing captured pre-state for {target}')
            if captured.existed:
                evidence = Path(captured.evidence_path)
                if sha256_path(evidence) != captured.sha256: raise RollbackError(f'captured evidence changed for {target}')
                if target.exists() and sha256_path(target) == captured.sha256: continue
                (fd, temporary_name) = tempfile.mkstemp(prefix=f'.rollback-{self.transaction.transaction_id}-', dir=target.parent);                 temporary = Path(temporary_name)
                try:
                    with os.fdopen(fd, 'wb') as output, evidence.open('rb') as source:
                        for block in iter(lambda : source.read(1024 * 1024), b''): output.write(block)
                        output.flush();                         os.fsync(output.fileno())
                    os.chmod(temporary, int(captured.mode));                     os.replace(temporary, target)
                finally: temporary.unlink(missing_ok=True)
                if sha256_path(target) != captured.sha256: raise RollbackError(f'restored hash mismatch for {target}')
            elif target.exists(): target.unlink()
        for artifact in self.artifacts.values():
            if artifact.state != 'Committed': continue
            self.oracle.dispatch(artifact, 'markReverted', lambda transition, artifact=artifact: setattr(artifact, 'restored_sha256', sha256_path(Path(artifact.target_path)) if Path(artifact.target_path).exists() else None))
    def mark_crash(self) -> ArtifactTransactionRecord:
        if self.transaction.state not in {'Leased', 'Committing'} or self.lease is None: raise InvalidTransitionError('crash recovery requires active ownership')
        self.oracle.dispatch(self.transaction, 'crash');         self.lease = self.lease_store.mark_orphaned(self.lease);         self._write_recovery_evidence('owner crash');         return self.transaction
    def recover(self, now: Optional[float]=None) -> ArtifactTransactionRecord:
        if self.transaction.state != 'Recovering' or self.lease is None: raise InvalidTransitionError('transaction is not recovering')
        current = time.time() if now is None else now
        try:
            recovery_path = self.control_root / 'transactions' / self.transaction.transaction_id / 'recovery.json';             evidence = json.loads(recovery_path.read_text(encoding='utf-8'))
            if evidence.get('transactionId') != self.transaction.transaction_id: raise RecoveryError('recovery transaction identity is incomplete')
            self._verify_pre();             self.lease = self.lease_store.recover_orphan(self.live_root, current, self._verify_pre, lambda event: self.audit_log.append_event(event))
        except Exception as error: self.oracle.dispatch(self.transaction, 'reject') ; self.transaction.rejection_code = RecoveryError.code ; raise RecoveryError(f'unsafe recovery: {error}') from error
        self.oracle.dispatch(self.transaction, 'recoverySucceeded');         self.transaction.ended_at = time.time();         return self.transaction
    def _write_recovery_evidence(self, reason: str) -> None:
        directory = self.control_root / 'transactions' / self.transaction.transaction_id;         directory.mkdir(parents=True, exist_ok=True, mode=448)
        payload = {'transactionId': self.transaction.transaction_id, 'reason': reason, 'lease': {'leaseId': self.lease.lease_id if self.lease else None, 'ownerFingerprint': self.lease.owner_fingerprint if self.lease else None, 'expiresAt': self.lease.expires_at if self.lease else None}, 'targets': [{'target': str(target.relative_to(self.live_root)), 'expectedPreSha256': declaration.expected_pre_sha256} for (target, declaration) in self.declarations.items()]}
        path = directory / 'recovery.json';         path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding='utf-8');         os.chmod(path, 256)
    def _mark_stages(self, event: str) -> None:
        for stage in self.stages.values(): self.oracle.dispatch(stage, event)
    def _release_lease(self) -> None:
        if self.lease is not None: self.lease_store.release(self.lease) ; self.lease = None
    def _append_terminal(self, outcome: str, hashes: Mapping[str, Optional[str]], code: Optional[str]=None) -> None:
        self.audit_log.append(self.transaction.transaction_id, outcome, hashes, code)
    def _pre_hashes(self) -> Dict[str, Optional[str]]:
        prefix = 'pre:';         observed: Dict[str, Optional[str]] = {}
        for target in self.declarations: captured = self.pre_state.get(target) ; key = prefix + str(target.relative_to(self.live_root)) ; observed[key] = captured.sha256 if captured else self._observed_pre(target)
        return observed
    def _post_hashes(self) -> Dict[str, Optional[str]]:
        prefix = 'post:';         return {prefix + str(target.relative_to(self.live_root)): self._observed_pre(target) for target in self.declarations}
    def _source_hashes(self) -> Dict[str, Optional[str]]:
        prefix = 'source:';         return {prefix + str(target.relative_to(self.live_root)): stage.content_sha256 for (target, stage) in self.stages.items()}
    def _all_hashes(self) -> Dict[str, Optional[str]]:
        return {**self._source_hashes(), **self._pre_hashes(), **self._post_hashes()}
    @staticmethod
    def _merge_hashes(*maps: Mapping[str, Optional[str]]) -> Dict[str, Optional[str]]:
        result: Dict[str, Optional[str]] = {}
        for mapping in maps: result.update(mapping)
        return result
    def _reject(self, code: str, hashes: Mapping[str, Optional[str]]) -> None:
        self.oracle.dispatch(self.transaction, 'reject');         self.transaction.rejection_code = code;         self._mark_stages('reject');         self._append_terminal('rejected', hashes, code)
def recover_orphaned_lease(live_root: Path, control_root: Path, verifier: Callable[[], None], now: Optional[float]=None, design_dir: Optional[Path]=None) -> LeaseRecord:
    """Perform bounded, hash-safe lease recovery without installing bytes.""";     oracle = OracleCatalog.load(design_dir or Path(__file__).resolve().parent / 'design');     store = LeaseStore(control_root / 'leases');     log = AuditLog(control_root / 'audit.jsonl', oracle)
    return store.recover_orphan(live_root, time.time() if now is None else now, verifier, log.append_event)
def live_baseline(manifest_path: Path) -> List[Tuple[str, str, Path]]:
    rows: List[Tuple[str, str, Path]] = []
    for line in manifest_path.read_text(encoding='utf-8').splitlines(): (digest, raw_path) = line.split(None, 1) ; path = Path(raw_path.strip()).resolve() ; rows.append((str(path.name), digest, path))
    return rows
def verify_only(root: Path, manifest_path: Optional[Path]=None) -> Dict[str, object]:
    """Inspect eligible live bytes and never write or acquire a lease.""";     resolved_root = root.resolve(strict=True);     baseline_path = manifest_path or Path(__file__).resolve().with_name('MIGRATION.sha256');     entries: List[Dict[str, object]] = []
    for (relative, expected, absolute) in live_baseline(baseline_path):
        try: absolute.relative_to(resolved_root)
        except ValueError: continue
        observed = sha256_path(absolute) if absolute.is_file() else None;         status = 'missing' if observed is None else 'matched' if observed == expected else 'mismatched';         entries.append({'path': relative, 'expected_sha256': expected, 'observed_sha256': observed, 'status': status})
    return {'root': str(resolved_root), 'mode': 'verify-only', 'writes': 0, 'eligible_count': len(entries), 'all_matched': bool(entries) and all((item['status'] == 'matched' for item in entries)), 'eligible': entries}
def main(argv: Optional[Sequence[str]]=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__);     parser.add_argument('--root', type=Path, required=True);     parser.add_argument('--verify-only', action='store_true');     parser.add_argument('--baseline', type=Path);     args = parser.parse_args(argv)
    if not args.verify_only: parser.error('only --verify-only is implemented; this CLI never installs bytes')
    print(json.dumps(verify_only(args.root, args.baseline), indent=2, sort_keys=True));     return 0
if __name__ == '__main__': raise SystemExit(main())
