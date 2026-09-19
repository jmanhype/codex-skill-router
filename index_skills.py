#!/usr/bin/env python3
"""Build the local Codex skill-router full-text index."""

from __future__ import annotations

import argparse
import hashlib
from contextlib import suppress
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.json"
FRONTMATTER_KEY = re.compile(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$")
MAX_BODY_CHARS = 120_000
MAX_DESCRIPTION_CHARS = 20_000
MAX_HEADING_CHARS = 20_000
SCHEMA_VERSION = "2"


class FreshnessDeadlineExceeded(RuntimeError):
    """Raised when a bounded freshness operation cannot finish in time."""


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    roots = data.get("roots")
    if not isinstance(roots, list) or not all(isinstance(item, str) for item in roots):
        raise ValueError("config roots must be a list of strings")
    data["roots"] = [str(Path(item).expanduser()) for item in roots]
    return data


def _deadline_reached(deadline: Optional[float]) -> bool:
    return deadline is not None and time.monotonic() >= deadline


def discover_skill_paths(
    roots: Iterable[str], deadline: Optional[float] = None
) -> Set[str]:
    """Return canonical SKILL.md paths without watching or touching the network."""
    paths: Set[str] = set()
    for root_text in roots:
        root = Path(root_text)
        if not root.exists():
            continue
        for path in sorted(root.rglob("SKILL.md")):
            if _deadline_reached(deadline):
                raise FreshnessDeadlineExceeded
            try:
                paths.add(str(path.resolve()))
            except OSError:
                continue
    return paths


def _safe_stat(path: Path) -> Optional[Tuple[int, int]]:
    try:
        stat = path.stat()
        return stat.st_mtime_ns, stat.st_size
    except OSError:
        return None


def file_fingerprint(path: Path) -> Optional[Dict[str, int | str]]:
    """Hash a skill only after its stat signature changes."""
    for _ in range(2):
        before = _safe_stat(path)
        if before is None:
            return None
        try:
            content = path.read_bytes()
        except OSError:
            return None
        after = _safe_stat(path)
        if after is not None and after == before:
            return {
                "mtime_ns": before[0],
                "size": before[1],
                "sha256": hashlib.sha256(content).hexdigest(),
            }
    return None


def manifest_snapshot(
    roots: Sequence[str],
    included_paths: Set[str],
    deadline: Optional[float] = None,
) -> List[Tuple[str, int, int, Optional[str], int]]:
    snapshot: List[Tuple[str, int, int, Optional[str], int]] = []
    for path_text in sorted(discover_skill_paths(roots, deadline)):
        if _deadline_reached(deadline):
            raise FreshnessDeadlineExceeded
        fingerprint = file_fingerprint(Path(path_text))
        if fingerprint is None:
            continue
        snapshot.append(
            (
                path_text,
                int(fingerprint["mtime_ns"]),
                int(fingerprint["size"]),
                str(fingerprint["sha256"]),
                int(path_text in included_paths),
            )
        )
    return snapshot


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    values: Dict[str, str] = {}
    index = 1
    while index < len(lines):
        line = lines[index]
        if line.strip() == "---":
            return values, "\n".join(lines[index + 1 :])

        match = FRONTMATTER_KEY.match(line)
        if match:
            key, value = match.group(1).lower(), match.group(2).strip()
            if value in {"|", ">"}:
                block: List[str] = []
                index += 1
                while index < len(lines):
                    nested = lines[index]
                    if nested.strip() and not nested.startswith((" ", "\t")):
                        break
                    if nested.strip():
                        block.append(nested.strip())
                    index += 1
                values[key] = "\n".join(block).strip()
                continue
            if value:
                values[key] = value
        index += 1

    # Malformed or unterminated front matter: index the whole file.
    return {}, text


def safe_text(value: Any, fallback: str = "") -> str:
    if not isinstance(value, str):
        return fallback
    cleaned = value.replace("\x00", " ").strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
        cleaned = cleaned[1:-1].strip()
    return cleaned


def extract_headings(body: str) -> str:
    headings: List[str] = []
    size = 0
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                headings.append(heading)
                size += len(heading) + 1
                if size >= MAX_HEADING_CHARS:
                    break
    return "\n".join(headings)


def skill_records(
    roots: Iterable[str], deadline: Optional[float] = None
) -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    seen_names = set()
    seen_paths = set()

    for priority, root_text in enumerate(roots):
        root = Path(root_text)
        if not root.exists():
            continue
        for path in sorted(root.rglob("SKILL.md")):
            if _deadline_reached(deadline):
                raise FreshnessDeadlineExceeded
            try:
                resolved = path.resolve()
                canonical = str(resolved)
            except OSError:
                canonical = str(path)
            if canonical in seen_paths:
                continue
            seen_paths.add(canonical)

            try:
                text = resolved.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            frontmatter, body = parse_frontmatter(text)
            name = safe_text(frontmatter.get("name"), resolved.parent.name)
            logical_name = name.casefold()
            if logical_name in seen_names:
                continue
            seen_names.add(logical_name)

            description = safe_text(frontmatter.get("description"))[:MAX_DESCRIPTION_CHARS]
            if not description:
                first_paragraph: List[str] = []
                for line in body.splitlines():
                    if line.strip():
                        first_paragraph.append(line.strip())
                    elif first_paragraph:
                        break
                description = " ".join(first_paragraph)[:2000]

            records.append(
                {
                    "name": name[:300],
                    "description": description,
                    "headings": extract_headings(body)[:MAX_HEADING_CHARS],
                    "body": body[:MAX_BODY_CHARS],
                    "path": canonical,
                    "root": str(root),
                    "priority": str(priority),
                }
            )

    return records


def build_database(
    output: Path,
    records: List[Dict[str, str]],
    roots: Optional[Sequence[str]] = None,
    deadline: Optional[float] = None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + f".tmp-{os.getpid()}")
    try:
        connection = sqlite3.connect(temporary)
        connection.execute(
            """
            CREATE VIRTUAL TABLE skills USING fts5(
                name,
                description,
                headings,
                body,
                path UNINDEXED,
                root UNINDEXED,
                priority UNINDEXED,
                tokenize='porter unicode61 remove_diacritics 2'
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE skill_manifest (
                path TEXT PRIMARY KEY,
                mtime_ns INTEGER NOT NULL,
                size INTEGER NOT NULL,
                sha256 TEXT,
                included INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX skill_manifest_included_idx ON skill_manifest(included)"
        )
        connection.executemany(
            """
            INSERT INTO skills
                (name, description, headings, body, path, root, priority)
            VALUES
                (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["name"],
                    item["description"],
                    item["headings"],
                    item["body"],
                    item["path"],
                    item["root"],
                    item["priority"],
                )
                for item in records
            ],
        )
        included_paths = {item["path"] for item in records}
        manifest = (
            manifest_snapshot(list(roots), included_paths, deadline)
            if roots is not None
            else [
                (
                    item["path"],
                    *_stat_or_zero(item["path"]),
                    None,
                    1,
                )
                for item in records
            ]
        )
        connection.executemany(
            """
            INSERT INTO skill_manifest
                (path, mtime_ns, size, sha256, included)
            VALUES (?, ?, ?, ?, ?)
            """,
            manifest,
        )
        connection.execute(
            "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            [
                ("schema_version", SCHEMA_VERSION),
                ("skill_count", str(len(records))),
                ("manifest_count", str(len(manifest))),
                ("generated_at", str(int(time.time()))),
                ("generated_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
            ],
        )
        connection.commit()
        connection.close()
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
        os.chmod(output, 0o600)
    finally:
        if temporary.exists():
            with suppress(OSError):
                temporary.unlink()


def _stat_or_zero(path: str) -> Tuple[int, int]:
    stat = _safe_stat(Path(path))
    return stat if stat is not None else (0, 0)


def index_freshness(
    database: Path,
    roots: Sequence[str],
    deadline: Optional[float] = None,
) -> Dict[str, Any]:
    """Check source stats/hashes and update touch-only manifest stats."""
    if not database.is_file():
        return {"refresh_needed": True, "reason": "database_missing"}

    try:
        connection = sqlite3.connect(
            f"file:{database}?mode=ro", uri=True, timeout=0.05
        )
        try:
            schema_row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if schema_row is None or schema_row[0] != SCHEMA_VERSION:
                return {"refresh_needed": True, "reason": "schema_upgrade"}
            quick_check = connection.execute("PRAGMA quick_check").fetchone()
            if quick_check is None or quick_check[0] != "ok":
                return {"refresh_needed": True, "reason": "database_unreadable"}
            manifest = {
                str(path): (int(mtime_ns), int(size), sha256)
                for path, mtime_ns, size, sha256 in connection.execute(
                    "SELECT path, mtime_ns, size, sha256 FROM skill_manifest"
                )
            }
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return {"refresh_needed": True, "reason": "database_unreadable"}

    current_paths = discover_skill_paths(roots, deadline)
    reasons: Set[str] = set()
    stat_updates: Dict[str, Tuple[int, int]] = {}

    for path_text in current_paths:
        previous = manifest.get(path_text)
        current_stat = _safe_stat(Path(path_text))
        if current_stat is None:
            continue
        if previous is None:
            reasons.add("source_set_changed")
            continue
        if current_stat == previous[:2]:
            continue

        fingerprint = file_fingerprint(Path(path_text))
        if fingerprint is None:
            reasons.add("source_unreadable")
            continue
        if str(fingerprint["sha256"]) != previous[2]:
            reasons.add("content_changed")
            continue
        stat_updates[path_text] = (
            int(fingerprint["mtime_ns"]),
            int(fingerprint["size"]),
        )

    if set(manifest) - current_paths:
        reasons.add("source_set_changed")

    if stat_updates:
        try:
            connection = sqlite3.connect(database, timeout=0.05)
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.executemany(
                    """
                    UPDATE skill_manifest
                    SET mtime_ns = ?, size = ?
                    WHERE path = ?
                    """,
                    [(mtime, size, path) for path, (mtime, size) in stat_updates.items()],
                )
                connection.commit()
            finally:
                connection.close()
        except (OSError, sqlite3.Error):
            return {"refresh_needed": True, "reason": "manifest_update_failed"}

    return {
        "refresh_needed": bool(reasons),
        "reason": ",".join(sorted(reasons)) or "current",
        "manifest_updated": bool(stat_updates),
    }


def ensure_fresh_index(
    config: Dict[str, Any], budget_seconds: float = 1.25
) -> Dict[str, Any]:
    """Refresh at most once per invocation, bounded and entirely locally."""
    deadline = time.monotonic() + max(0.0, budget_seconds)
    database = Path(str(config.get("database", "")))
    roots = [str(root) for root in config.get("roots", [])]

    try:
        status = index_freshness(database, roots, deadline)
    except FreshnessDeadlineExceeded:
        return {
            "refresh_needed": False,
            "reason": "deadline_exceeded",
            "deadline_exceeded": True,
        }
    except (OSError, sqlite3.Error) as error:
        return {
            "refresh_needed": False,
            "reason": f"refresh_error:{error}",
            "refresh_failed": True,
        }

    if not status["refresh_needed"]:
        return status
    if _deadline_reached(deadline - 0.25):
        return {**status, "deadline_exceeded": True}

    try:
        records = skill_records(roots, deadline - 0.10)
        if _deadline_reached(deadline - 0.25):
            return {**status, "deadline_exceeded": True}
        build_database(database, records, roots, deadline)
    except FreshnessDeadlineExceeded:
        return {**status, "deadline_exceeded": True}
    except Exception as error:
        return {**status, "refresh_failed": True, "error": str(error)}

    return {**status, "rebuilt": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        records = skill_records(config["roots"])
        database = Path(config["database"])
        build_database(database, records, config["roots"])
        if not args.quiet:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "database": str(database),
                        "skill_count": len(records),
                    },
                    sort_keys=True,
                )
            )
        return 0
    except Exception as error:  # Index maintenance is manual and reportable here.
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
