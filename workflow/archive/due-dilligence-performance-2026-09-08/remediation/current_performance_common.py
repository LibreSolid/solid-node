#!/usr/bin/env python3
"""Shared safety and provenance helpers for current-candidate measurements.

This module is new remediation harness code.  It deliberately does not import
the immutable historical probe, and it never writes anywhere except a caller's
explicit evidence path or a verified disposable project copy.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Iterable


HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent / "performance"
REPO = HERE.parents[2]
SHOP = REPO.parents[2]
EXPECTED_CATALOGUE = SHOP / "projects"
PLANNING_HEAD = "2ca4b9f06835d1133b6ad00eceecdee6e29b714c"
PLANNING_BASELINE_HEAD = "4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c"
PROJECTS = (
    "Vibecoded-demos/abacus",
    "Vibecoded-demos/v8-engine",
    "3D-Printers/Metamaquina2",
)
SECTIONS = (
    "startup",
    "build",
    "batch",
    "projects",
    "empirical",
    "algorithms",
    "memory",
)
INPUT_SUFFIXES = {".py", ".toml", ".scad", ".js", ".step", ".stp", ".stl"}
LABEL = re.compile(r"[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])?\Z")
CANDIDATE_ENV = "SOLID_NODE_PERFORMANCE_CANDIDATE_SHA256"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=path, text=True, stderr=subprocess.STDOUT
    ).strip()


def validate_label(label: str) -> str:
    """Require a short, safe, single output-name component."""
    if not LABEL.fullmatch(label):
        raise ValueError(
            "label must be one 1-64 character lowercase component using "
            "letters, digits, '_' or '-', with an alphanumeric first/last "
            "character"
        )
    if Path(label).name != label or label in {".", ".."}:
        raise ValueError("label must be one path component")
    return label


def write_new(path: Path, content: bytes) -> None:
    """Atomically publish a new evidence file, refusing any overwrite."""
    path = path.resolve(strict=False)
    if path.parent != HERE.resolve():
        raise ValueError(f"evidence output must be directly under {HERE}: {path}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        # link(2), unlike replace(2), is atomic and fails if the target exists.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_new_json(path: Path, value: object) -> None:
    write_new(path, json.dumps(value, indent=2, sort_keys=True).encode() + b"\n")


def _nul_git(repo: Path, *args: str) -> set[str]:
    output = subprocess.check_output(["git", *args], cwd=repo)
    return {item.decode("utf-8", "surrogateescape")
            for item in output.split(b"\0") if item}


def _inventory_paths(path: Path) -> set[str]:
    result = set()
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        _, relative = line.split(maxsplit=1)
        result.add(relative)
    return result


def candidate_path_set(repo: Path = REPO) -> set[str]:
    """All content whose bytes define the measured implementation candidate.

    The union begins at planning HEAD so a staged or unstaged deletion remains
    an explicit manifest entry.  It then adds index and non-ignored untracked
    paths.  Generated evidence is absent by construction: remediation Python
    harness code is included, but arbitrary JSON/XML/MD/log output is not.
    """
    head = _nul_git(repo, "ls-tree", "-rz", "--name-only", "HEAD")
    current = _nul_git(
        repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard"
    )
    fixed = {
        "workflow/due-dilligence-performance/remediation/historical.sha256",
        "workflow/due-dilligence-performance/remediation/planning-head-baseline.sha256",
    }
    for inventory in tuple(fixed):
        path = repo / inventory
        if path.is_file():
            fixed.update(_inventory_paths(path))

    def selected(relative: str) -> bool:
        path = Path(relative)
        return (
            relative == "solid_node" or relative.startswith("solid_node/")
            or relative == "tests" or relative.startswith("tests/")
            or relative in fixed
            or relative.startswith(
                "workflow/due-dilligence-performance/performance/fixtures/"
            )
            or (
                relative.startswith(
                    "workflow/due-dilligence-performance/remediation/"
                )
                and (path.suffix == ".py" or "fixed-fixtures" in path.parts)
            )
        )

    return {relative for relative in head | current if selected(relative)}


def candidate_identity(
    repo: Path = REPO,
    *,
    expected_head: str | None = PLANNING_HEAD,
    paths: Iterable[str] | None = None,
) -> dict[str, object]:
    """Hash planning HEAD plus actual tracked/untracked/deleted candidate bytes."""
    repo = repo.resolve()
    head = git(repo, "rev-parse", "HEAD")
    if expected_head is not None and head != expected_head:
        raise ValueError(
            f"candidate must still be based at planning HEAD {expected_head}; "
            f"found {head}"
        )
    dynamic_paths = paths is None
    selected_paths = set(paths if paths is not None else candidate_path_set(repo))
    entries = []
    for relative in sorted(selected_paths):
        path = repo / relative
        try:
            stat = path.lstat()
        except FileNotFoundError:
            entries.append({"path": relative, "kind": "deleted"})
            continue
        if path.is_symlink():
            target = os.readlink(path)
            if path.lstat() != stat or os.readlink(path) != target:
                raise ValueError(f"candidate symlink changed while hashed: {relative}")
            entries.append({
                "path": relative,
                "kind": "symlink",
                "target": target,
                "sha256": hashlib.sha256(os.fsencode(target)).hexdigest(),
            })
        elif path.is_file():
            content_sha256 = sha256(path)
            after = path.lstat()
            stable_fields = (
                "st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns"
            )
            if any(getattr(stat, field) != getattr(after, field)
                   for field in stable_fields):
                raise ValueError(f"candidate file changed while hashed: {relative}")
            entries.append({
                "path": relative,
                "kind": "file",
                "bytes": stat.st_size,
                "executable": bool(stat.st_mode & 0o111),
                "sha256": content_sha256,
            })
        else:
            raise ValueError(f"candidate path is not a file/symlink: {relative}")
    if git(repo, "rev-parse", "HEAD") != head:
        raise ValueError("planning HEAD changed while candidate identity was computed")
    if dynamic_paths and candidate_path_set(repo) != selected_paths:
        raise ValueError("candidate path set changed while identity was computed")
    payload = {
        "identity_schema": "solid-node-uncommitted-candidate-v2",
        "planning_head": head,
        "entries": entries,
    }
    return {
        **payload,
        "content_sha256": hashlib.sha256(canonical_json(payload)).hexdigest(),
        "entry_count": len(entries),
    }


def verify_sha_inventory(inventory: Path, repo: Path = REPO) -> dict[str, object]:
    entries = []
    for line in inventory.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        expected, relative = line.split(maxsplit=1)
        path = repo / relative
        actual = sha256(path)
        entries.append({
            "path": relative,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches": actual == expected,
        })
    result = {
        "inventory": str(inventory.relative_to(repo)),
        "inventory_sha256": sha256(inventory),
        "entry_count": len(entries),
        "all_match": all(entry["matches"] for entry in entries),
        "entries": entries,
    }
    if not result["all_match"]:
        bad = next(entry["path"] for entry in entries if not entry["matches"])
        raise ValueError(f"immutable inventory mismatch: {bad}")
    return result


def historical_inventory() -> dict[str, object]:
    return verify_sha_inventory(HERE / "historical.sha256")


def planning_baseline_inventory() -> dict[str, object]:
    result = verify_sha_inventory(HERE / "planning-head-baseline.sha256")
    section_heads = {}
    for section in SECTIONS:
        record = json.loads(
            (HERE / f"planning-head-baseline-{section}.json").read_text()
        )
        section_heads[section] = record["provenance"]["framework"]["commit"]
    observed = set(section_heads.values())
    if observed != {PLANNING_BASELINE_HEAD}:
        raise ValueError(
            "immutable planning baseline has unexpected framework HEADs: "
            f"{sorted(observed)}"
        )
    result.update({
        "planning_baseline_head": PLANNING_BASELINE_HEAD,
        "planning_baseline_section_heads": section_heads,
        "candidate_planning_head": PLANNING_HEAD,
        "heads_distinct": PLANNING_BASELINE_HEAD != PLANNING_HEAD,
    })
    if not result["heads_distinct"]:
        raise ValueError(
            "amended candidate planning HEAD was conflated with immutable baseline HEAD"
        )
    return result


def input_hashes(root: Path) -> dict[str, str]:
    """Match the immutable v1 wrapper's exact selected-input definition."""
    result = {}
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and "_build" not in path.parts
            and path.suffix.lower() in INPUT_SUFFIXES
        ):
            result[str(path.relative_to(root))] = sha256(path)
    return result


def catalogue_snapshot(catalogue: Path) -> dict[str, dict[str, object]]:
    catalogue = catalogue.resolve()
    if catalogue != EXPECTED_CATALOGUE.resolve():
        raise ValueError(f"catalogue must be exactly {EXPECTED_CATALOGUE}")
    result = {}
    for relative in PROJECTS:
        source = catalogue / relative
        top = Path(git(source, "rev-parse", "--show-toplevel"))
        if top != source:
            raise ValueError(f"not its own repository: {source} (reported {top})")
        result[relative] = {
            "path": str(source),
            "commit": git(source, "rev-parse", "HEAD"),
            "status": git(source, "status", "--short"),
            "input_sha256": input_hashes(source),
        }
    return result


def baseline_catalogue_snapshot() -> dict[str, dict[str, object]]:
    baseline = json.loads(
        (HERE / "planning-head-baseline-projects.json").read_text()
    )
    return baseline["original_catalogue_before"]


def require_baseline_catalogue(catalogue: Path) -> dict[str, dict[str, object]]:
    current = catalogue_snapshot(catalogue)
    expected = baseline_catalogue_snapshot()
    if current != expected:
        for project in PROJECTS:
            if current.get(project) != expected.get(project):
                raise ValueError(
                    f"original catalogue no longer matches planning baseline: {project}"
                )
        raise ValueError("original catalogue no longer matches planning baseline")
    return current


def require_disposable_target(target: Path, source: Path, catalogue: Path) -> None:
    """Reject any copy/build/restamp target that resolves into source data."""
    target_real = target.resolve(strict=False)
    source_real = source.resolve()
    catalogue_real = catalogue.resolve()
    if target_real == source_real or target_real.is_relative_to(source_real):
        raise ValueError(f"mutation target resolves inside original project: {target}")
    if target_real == catalogue_real or target_real.is_relative_to(catalogue_real):
        raise ValueError(f"mutation target resolves inside source catalogue: {target}")


def reject_escaping_symlinks(root: Path) -> None:
    root_real = root.resolve()
    for path in root.rglob("*"):
        if not path.is_symlink():
            continue
        resolved = path.resolve(strict=False)
        if resolved != root_real and not resolved.is_relative_to(root_real):
            raise ValueError(f"external symlink in disposable project: {path} -> {resolved}")


def copy_project(
    catalogue: Path, relative: str, target: Path
) -> tuple[Path, dict[str, object]]:
    if relative not in PROJECTS:
        raise ValueError(f"project is not in the fixed catalogue set: {relative}")
    catalogue = catalogue.resolve()
    source = catalogue / relative
    require_disposable_target(target, source, catalogue)
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"disposable target already exists: {target}")
    shutil.copytree(
        source,
        target,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".env", ".pytest_cache", ".venv",
            "node_modules", "*.pyc",
        ),
    )
    require_disposable_target(target, source, catalogue)
    reject_escaping_symlinks(target)
    source_hashes = input_hashes(source)
    copied_hashes = input_hashes(target)
    if copied_hashes != source_hashes:
        raise ValueError(f"disposable copy input mismatch: {relative}")
    return target, {
        "project": relative,
        "source": str(source),
        "target": str(target),
        "source_input_sha256": source_hashes,
        "copied_input_sha256": copied_hashes,
        "input_maps_equal": True,
    }


def artifact_state(project: Path) -> dict[str, object]:
    """Complete STL content map plus publication/fact/churn inputs."""
    build = project / "_build"
    stls = {
        str(path.relative_to(build)): sha256(path)
        for path in sorted(build.rglob("*.stl")) if path.is_file()
    } if build.exists() else {}
    document = build / "viewer.json"
    manifest = None
    manifest_summary = {
        "manifest_sha256": None,
        "stl_files": len(stls),
        "stl_bytes": 0,
        "pieces": None,
        "piece_instances": None,
    }
    files = {}
    if build.exists():
        for path in sorted(build.rglob("*")):
            if not path.is_file():
                continue
            stat = path.stat()
            files[str(path.relative_to(build))] = {
                "inode": stat.st_ino,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "ctime_ns": stat.st_ctime_ns,
                "sha256": sha256(path),
            }
    manifest_summary["stl_bytes"] = sum(
        record["size"] for name, record in files.items()
        if Path(name).suffix.lower() == ".stl"
    )
    if document.is_file():
        manifest = {
            "bytes": document.stat().st_size,
            "sha256": sha256(document),
        }
        manifest_data = json.loads(document.read_text())
        pieces = manifest_data.get("pieces", [])
        manifest_summary.update({
            "manifest_sha256": manifest["sha256"],
            "pieces": len(pieces),
            "piece_instances": sum(piece["count"] for piece in pieces),
        })
    return {
        "stl_filename_sha256": stls,
        "stl_files": len(stls),
        "manifest": manifest,
        "planning_baseline_comparable_summary": manifest_summary,
        "files": files,
    }


def artifact_churn(
    before: dict[str, object], after: dict[str, object]
) -> dict[str, object]:
    before_files = before["files"]
    after_files = after["files"]
    names = sorted(set(before_files) | set(after_files))
    changed = []
    summary: dict[str, dict[str, int]] = {}
    for name in names:
        old = before_files.get(name)
        new = after_files.get(name)
        if old == new:
            continue
        extension = Path(name).suffix or "<none>"
        counts = summary.setdefault(
            extension,
            {"added": 0, "removed": 0, "identity_changed": 0,
             "bytes_changed": 0, "same_bytes_identity_changed": 0},
        )
        if old is None:
            kind = "added"
            counts[kind] += 1
        elif new is None:
            kind = "removed"
            counts[kind] += 1
        else:
            identity_changed = any(old[key] != new[key]
                                   for key in ("inode", "mtime_ns", "ctime_ns"))
            bytes_changed = old["sha256"] != new["sha256"]
            if identity_changed:
                counts["identity_changed"] += 1
            if bytes_changed:
                counts["bytes_changed"] += 1
            if identity_changed and not bytes_changed:
                counts["same_bytes_identity_changed"] += 1
            kind = "changed"
        changed.append({"path": name, "kind": kind, "before": old, "after": new})
    return {"summary_by_suffix": summary, "changed": changed}


def validate_worker_tree(value: object, location: str = "measurements") -> int:
    """Recursively reject hidden subprocess errors, timeouts and statuses."""
    workers = 0
    if isinstance(value, dict):
        if value.get("worker_record") is True:
            workers += 1
            if value.get("status") != 0:
                raise ValueError(f"{location}: worker status {value.get('status')!r}")
            for key in ("timeout_s", "worker_error", "runner_error"):
                if key in value:
                    raise ValueError(f"{location}: worker contains {key}")
        elif isinstance(value.get("status"), int) and value["status"] != 0:
            # External helper scripts (WP8/WP9) are wrapped with a numeric
            # status but need not know this module's worker schema.
            raise ValueError(f"{location}: nested status {value['status']}")
        if "timeout_s" in value:
            raise ValueError(f"{location}: nested timeout")
        if "runner_error" in value or "worker_error" in value:
            raise ValueError(f"{location}: nested error")
        for key, child in value.items():
            workers += validate_worker_tree(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            workers += validate_worker_tree(child, f"{location}[{index}]")
    return workers


def require_worker_candidate(
    value: object, expected: str, location: str = "measurements"
) -> int:
    """Require every nested worker to name the section's frozen candidate."""
    workers = 0
    if isinstance(value, dict):
        if value.get("worker_record") is True:
            workers += 1
            if value.get("candidate_content_sha256") != expected:
                raise ValueError(f"{location}: worker candidate identity mismatch")
        for key, child in value.items():
            workers += require_worker_candidate(child, expected, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            workers += require_worker_candidate(child, expected, f"{location}[{index}]")
    return workers
