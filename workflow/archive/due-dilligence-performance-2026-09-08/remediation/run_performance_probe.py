#!/usr/bin/env python3
"""Run the immutable performance-audit probe into remediation evidence.

The historical probe remains unchanged.  This wrapper imports its measurement
functions, gives every section a fresh temporary directory, and writes labelled
outputs beside this file.  Project measurements additionally inventory the
three original catalogue repositories before and after the disposable-copy run.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent / "performance"
REPO = HERE.parents[2]
SHOP = REPO.parents[2]
EXPECTED_CATALOGUE = SHOP / "projects"
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=path, text=True).strip()


def load_audit_probe():
    path = AUDIT / "probe.py"
    spec = importlib.util.spec_from_file_location("historical_performance_probe", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load historical probe: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def input_hashes(root: Path) -> dict[str, str]:
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
    result = {}
    for relative in PROJECTS:
        source = catalogue / relative
        top = Path(git(source, "rev-parse", "--show-toplevel"))
        if top != source:
            raise ValueError(f"Not its own repository: {source} (reported {top})")
        result[relative] = {
            "path": str(source),
            "commit": git(source, "rev-parse", "HEAD"),
            "status": git(source, "status", "--short"),
            "input_sha256": input_hashes(source),
        }
    return result


def historical_inventory() -> dict[str, object]:
    inventory = HERE / "historical.sha256"
    entries = []
    for line in inventory.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        expected, relative = line.split(maxsplit=1)
        path = REPO / relative
        actual = sha256(path)
        entries.append(
            {
                "path": relative,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "matches": actual == expected,
            }
        )
    return {
        "inventory": str(inventory.relative_to(REPO)),
        "inventory_sha256": sha256(inventory),
        "entry_count": len(entries),
        "all_match": all(entry["matches"] for entry in entries),
        "entries": entries,
    }


def provenance(label: str, section: str, catalogue: Path | None) -> dict[str, object]:
    argv = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
    return {
        "label": label,
        "section": section,
        "command": {
            "argv": argv,
            "shell_equivalent": " ".join(argv),
            "cwd": str(REPO),
            "required_environment": {
                "PYTHONPATH": str(REPO),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        },
        "framework": {
            "repository": str(REPO),
            "commit": git(REPO, "rev-parse", "HEAD"),
            "branch": git(REPO, "branch", "--show-current"),
            "solid_node_tree": git(REPO, "rev-parse", "HEAD:solid_node"),
            "tests_tree": git(REPO, "rev-parse", "HEAD:tests"),
            "production_status": subprocess.check_output(
                ["git", "status", "--short", "--", "solid_node", "tests"],
                cwd=REPO,
                text=True,
            ).strip(),
        },
        "probe": {
            "path": str((AUDIT / "probe.py").relative_to(REPO)),
            "sha256": sha256(AUDIT / "probe.py"),
            "wrapper_path": str(Path(__file__).resolve().relative_to(REPO)),
            "wrapper_sha256": sha256(Path(__file__).resolve()),
            "fixture_input_sha256": input_hashes(AUDIT / "fixtures"),
        },
        "historical_inventory_before": historical_inventory(),
    }


def run_section(probe, label: str, section: str, catalogue: Path | None) -> Path:
    record = {
        "evidence_schema": "solid-node-performance-remediation-v1",
        "provenance": provenance(label, section, catalogue),
        "environment": probe.environment(),
        "section": section,
    }
    originals_before = None
    if section in ("projects", "empirical"):
        if catalogue is None:
            raise ValueError(f"{section} requires --catalogue")
        originals_before = catalogue_snapshot(catalogue)
        record["original_catalogue_before"] = originals_before

    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(
            prefix=f"solid-remediation-{label}-{section}-"
        ) as scratch:
            if section in ("projects", "empirical"):
                record["measurements"] = probe.project_probes(
                    scratch,
                    catalogue,
                    detail=section == "empirical",
                )
            elif section == "build":
                record["measurements"] = probe.build_probes(scratch)
            elif section == "batch":
                record["measurements"] = probe.batch_probes(scratch)
            else:
                project = Path(scratch) / "fixture"
                shutil.copytree(AUDIT / "fixtures", project)
                if section == "startup":
                    record["measurements"] = probe.startup_probes(project)
                else:
                    record["measurements"] = probe.invoke(section, project)
    except BaseException as exc:
        record["runner_error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        record["runner_wall_s"] = time.monotonic() - started
        record["historical_inventory_after"] = historical_inventory()
        if originals_before is not None:
            originals_after = catalogue_snapshot(catalogue)
            record["original_catalogue_after"] = originals_after
            record["original_catalogue_unchanged"] = originals_before == originals_after
        output = HERE / f"{label}-{section}.json"
        output.write_text(json.dumps(record, indent=2) + "\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--section", choices=SECTIONS)
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--label", required=True)
    parser.add_argument("--catalogue", type=Path)
    args = parser.parse_args()

    catalogue = args.catalogue.resolve() if args.catalogue else None
    chosen = SECTIONS if args.all else (args.section,)
    if any(section in ("projects", "empirical") for section in chosen):
        if catalogue is None:
            parser.error("project sections require --catalogue")
        if catalogue != EXPECTED_CATALOGUE.resolve():
            parser.error(
                f"refusing catalogue other than exact workspace input: {EXPECTED_CATALOGUE}"
            )

    probe = load_audit_probe()
    outputs = []
    for section in chosen:
        print(f"remediation probe: {label_section(args.label, section)}", flush=True)
        outputs.append(str(run_section(probe, args.label, section, catalogue)))
    print(json.dumps({"outputs": outputs}, indent=2))
    return 0


def label_section(label: str, section: str) -> str:
    return f"{label}/{section}"


if __name__ == "__main__":
    sys.exit(main())
