#!/usr/bin/env python3
"""Validate saved v2 current-candidate evidence without rerunning workloads."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from current_performance_common import (
    HERE,
    PLANNING_BASELINE_HEAD,
    PLANNING_HEAD,
    SECTIONS,
    candidate_identity,
    require_worker_candidate,
    sha256,
    validate_label,
    validate_worker_tree,
)
from run_current_performance_probe import verify_section


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--section", action="append", choices=SECTIONS)
    parser.add_argument("--require-current-candidate", action="store_true")
    parser.add_argument("--require-inventory", action="store_true")
    args = parser.parse_args()
    label = validate_label(args.label)
    sections = tuple(args.section or SECTIONS)
    identity_path = HERE / f"{label}-candidate-identity.json"
    identity = json.loads(identity_path.read_text())
    require(
        identity.get("identity_schema") == "solid-node-uncommitted-candidate-v2",
        "wrong candidate identity schema",
    )
    if args.require_current_candidate:
        require(candidate_identity() == identity, "working candidate has moved")

    worker_count = 0
    for section in sections:
        path = HERE / f"{label}-{section}.json"
        record = json.loads(path.read_text())
        require(
            record.get("evidence_schema") == "solid-node-performance-remediation-v2",
            f"{section}: wrong evidence schema",
        )
        require(record.get("label") == label, f"{section}: wrong label")
        require(record.get("section") == section, f"{section}: wrong section")
        require(
            identity.get("planning_head") == PLANNING_HEAD
            and record.get("planning_head") == PLANNING_HEAD,
            f"{section}: wrong amended candidate planning HEAD",
        )
        require("runner_error" not in record, f"{section}: runner error")
        require("postflight_error" not in record, f"{section}: postflight error")
        require(
            record.get("candidate_identity_before") == identity
            and record.get("candidate_identity_after") == identity
            and record.get("candidate_identity_unchanged") is True,
            f"{section}: candidate identity mismatch",
        )
        for key in (
            "historical_inventory_before", "historical_inventory_after",
            "planning_baseline_inventory_before", "planning_baseline_inventory_after",
        ):
            require(record[key]["all_match"], f"{section}: {key} mismatch")
        for key in (
            "planning_baseline_inventory_before",
            "planning_baseline_inventory_after",
        ):
            provenance = record[key]
            require(
                provenance.get("planning_baseline_head")
                == PLANNING_BASELINE_HEAD
                and provenance.get("candidate_planning_head") == PLANNING_HEAD
                and provenance.get("heads_distinct") is True,
                f"{section}: planning baseline/candidate HEAD provenance conflated",
            )
        if section in {"projects", "empirical"}:
            require(
                record.get("original_catalogue_unchanged") is True
                and record.get("original_catalogue_matches_planning_baseline") is True,
                f"{section}: original catalogue mismatch",
            )
        worker_count += validate_worker_tree(
            record["measurement_environment"], f"{section}.measurement_environment"
        )
        require_worker_candidate(
            record["measurement_environment"], identity["content_sha256"],
            f"{section}.measurement_environment",
        )
        worker_count += validate_worker_tree(record["measurements"], section)
        require_worker_candidate(
            record["measurements"], identity["content_sha256"], section
        )
        verify_section(section, record["measurements"])

    inventory_path = HERE / f"{label}-evidence-inventory.json"
    if inventory_path.exists():
        inventory = json.loads(inventory_path.read_text())
        require(inventory.get("label") == label, "evidence inventory label mismatch")
        require(
            inventory.get("candidate_content_sha256") == identity["content_sha256"],
            "evidence inventory candidate mismatch",
        )
        for entry in inventory["entries"]:
            path = HERE.parents[2] / entry["path"]
            require(path.stat().st_size == entry["bytes"],
                    f"evidence size mismatch: {entry['path']}")
            require(sha256(path) == entry["sha256"],
                    f"evidence digest mismatch: {entry['path']}")
    elif args.require_inventory:
        raise ValueError(f"missing evidence inventory: {inventory_path}")

    print(
        f"Verified {worker_count} successful nested workers across "
        f"{len(sections)} v2 sections for {identity['content_sha256']}."
    )
    print("Candidate, historical evidence, planning baseline, project provenance, "
          "and structural/equivalence gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
