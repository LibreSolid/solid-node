#!/usr/bin/env python3
"""Validate saved audit evidence without executing projects or asserting timings."""

import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
BASE = "4bf9b69421b7114809af75fe663441d115407631"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def workers(value):
    if isinstance(value, dict):
        if "wall_s" in value:
            yield value
        for child in value.values():
            yield from workers(child)
    elif isinstance(value, list):
        for child in value:
            yield from workers(child)


def main():
    records = {}
    worker_count = 0
    for name in ("startup", "build", "batch", "projects", "empirical", "algorithms", "memory"):
        record = json.loads((HERE / f"{name}.json").read_text())
        require(record["environment"]["framework_commit"] == BASE, f"{name}: base changed")
        require(record["section"] == name, f"{name}: wrong section")
        found = list(workers(record["measurements"]))
        require(bool(found), f"{name}: no worker evidence")
        for index, worker in enumerate(found):
            require(worker.get("status") == 0, f"{name} worker {index}: failed")
            require("error" not in worker and "timeout_s" not in worker,
                    f"{name} worker {index}: error/timeout")
        worker_count += len(found)
        records[name] = record["measurements"]

    for record in records["build"]:
        require(record["manifest_unchanged"], "Fixture unchanged-build artifacts changed")
        require(record["artifacts"]["stl_files"] == record["count"], "Fixture STL count")
    for record in records["batch"]:
        require(record["stl_hashes_identical"] and record["stl_files"] == 24,
                "Batch output differs")
    for section in ("projects", "empirical"):
        require(len(records[section]) == 3, f"{section}: missing project")
        for record in records[section]:
            require(record["status_before"] == record["status_after"],
                    f"{record['project']}: original working state changed")
            require(bool(record["source_sha256"]), "Missing input provenance")
            if section == "projects":
                require(record["manifest_unchanged"], "Project publication changed")
            else:
                detail = record["detail"]
                require(detail["reuse_manifest_identical"], "Fact reuse changed manifest")
                require(detail["sweep_candidate_sets_identical"], "Candidate sets differ")
                if "flexible" in detail:
                    require(detail["flexible"]["interleaved_volumes_identical"],
                            "Flexible-cache volumes differ")
    for record in records["algorithms"]["sweep"]:
        require(record["result"] == 0, "Disjoint-box probe returned candidates")
    require(records["memory"]["placements"][-1]["cache_entries"] == 4000,
            "Placement retention observation changed")

    suite = ET.parse(HERE / "validation.xml").getroot().find("testsuite")
    require(suite is not None, "Missing framework suite")
    require(suite.get("failures") == "0" and suite.get("errors") == "0", "Suite failed")
    require(suite.get("tests") == "1801" and suite.get("skipped") == "16",
            "Suite case/skip counts changed")
    print(f"Verified {worker_count} successful workers across 7 sections.")
    print("Artifact equivalence, project provenance, candidate/volume checks: passed.")
    print("Framework JUnit: 1801 cases including subtests; 16 skipped; no failures/errors.")
    print("Initial failed empirical run is intentionally retained and excluded.")


if __name__ == "__main__":
    main()
