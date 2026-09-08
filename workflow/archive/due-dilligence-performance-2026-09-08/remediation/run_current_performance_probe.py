#!/usr/bin/env python3
"""Run v2 performance probes against one cryptographically frozen candidate.

The runner is intentionally separate from the immutable v1 baseline wrapper.
It measures only disposable fixture/project copies, records the candidate
identity before and after every section, rejects nested worker failures even
when a wrapper process returned zero, and never overwrites evidence.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import traceback

from current_performance_common import (
    AUDIT,
    CANDIDATE_ENV,
    EXPECTED_CATALOGUE,
    HERE,
    PLANNING_HEAD,
    PROJECTS,
    REPO,
    SECTIONS,
    artifact_churn,
    artifact_state,
    candidate_identity,
    catalogue_snapshot,
    copy_project,
    historical_inventory,
    input_hashes,
    planning_baseline_inventory,
    reject_escaping_symlinks,
    require_worker_candidate,
    require_baseline_catalogue,
    sha256,
    validate_label,
    validate_worker_tree,
    write_new_json,
)


WORKER = HERE / "current_performance_worker.py"
WP8 = HERE / "wp8_probe.py"
WP9 = HERE / "wp9_probe.py"
MARKER = "CURRENT_PERFORMANCE_RESULT="
PLANNING_MAP_BLINDSPOT = (
    "The immutable v1 planning baseline retained aggregate STL count/bytes and "
    "manifest SHA-256, but no complete filename-to-SHA-256 map. Its batch probe "
    "computed two maps and retained only their equality verdict and file count. "
    "Candidate full maps are retained here, but current self-equivalence is not "
    "claimed as planning-baseline-to-candidate byte equivalence."
)


def _worker_command(mode: str, *arguments: str) -> list[str]:
    return [sys.executable, str(WORKER), "--mode", mode, *arguments]


def verified_worker_cwd(cwd: Path) -> Path:
    """Return a real disposable worker directory, never a source scope."""
    resolved = cwd.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError(f"worker cwd is not a directory: {cwd}")
    repo = REPO.resolve(strict=True)
    catalogue = EXPECTED_CATALOGUE.resolve(strict=True)
    if resolved == repo or resolved.is_relative_to(repo):
        raise ValueError(f"worker cwd resolves inside framework source: {cwd}")
    if resolved == catalogue or resolved.is_relative_to(catalogue):
        raise ValueError(f"worker cwd resolves inside source catalogue: {cwd}")
    return resolved


def invoke(
    command: list[str], cwd: Path, *, timeout: int = 420, profile: bool = False
) -> dict[str, object]:
    cwd = verified_worker_cwd(cwd)
    pythonpath_entries = [str(REPO.resolve(strict=True)), str(cwd)]
    effective_pythonpath = os.pathsep.join(pythonpath_entries)
    env = dict(
        os.environ,
        PYTHONPATH=effective_pythonpath,
        PYTHONDONTWRITEBYTECODE="1",
    )
    env.pop("SOLID_BUILD_DIR", None)
    env.pop("SOLID_TEST_KERNEL", None)
    env.pop("SOLID_TEST_VOLUME_EPSILON", None)
    if profile:
        command = [*command, "--profile"]
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        return {
            "worker_record": True,
            "worker_schema": "solid-node-performance-worker-v2",
            "status": process.returncode,
            "timeout_s": timeout,
            "outer_wall_s": time.perf_counter() - started,
            "stdout": stdout[-16000:],
            "stderr": stderr[-16000:],
            "command": command,
            "cwd": str(cwd),
            "effective_pythonpath": effective_pythonpath,
            "pythonpath_entries": pythonpath_entries,
        }
    lines = [line for line in stdout.splitlines() if line.startswith(MARKER)]
    if len(lines) != 1:
        return {
            "worker_record": True,
            "worker_schema": "solid-node-performance-worker-v2",
            "status": process.returncode or 1,
            "worker_error": f"expected one result marker, found {len(lines)}",
            "outer_wall_s": time.perf_counter() - started,
            "stdout": stdout[-16000:],
            "stderr": stderr[-16000:],
            "command": command,
            "cwd": str(cwd),
            "effective_pythonpath": effective_pythonpath,
            "pythonpath_entries": pythonpath_entries,
        }
    record = json.loads(lines[0][len(MARKER):])
    record.update({
        "outer_wall_s": time.perf_counter() - started,
        "process_status": process.returncode,
        "stdout": "\n".join(
            line for line in stdout.splitlines() if not line.startswith(MARKER)
        )[-16000:],
        "stderr": stderr[-16000:],
        "command": command,
        "cwd": str(cwd),
        "effective_pythonpath": effective_pythonpath,
        "pythonpath_entries": pythonpath_entries,
    })
    # A worker cannot launder its real process result through its JSON status.
    if process.returncode != 0 and record.get("status") == 0:
        record["status"] = process.returncode
    return record


def invoke_external(
    script: Path, arguments: list[str], *, timeout: int = 420
) -> dict[str, object]:
    command = [sys.executable, str(script), *arguments]
    env = dict(os.environ, PYTHONPATH=str(REPO), PYTHONDONTWRITEBYTECODE="1")
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=REPO,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        return {
            "worker_record": True,
            "worker_schema": "solid-node-external-probe-v2",
            "status": process.returncode,
            "timeout_s": timeout,
            "outer_wall_s": time.perf_counter() - started,
            "stdout": stdout[-16000:],
            "stderr": stderr[-16000:],
            "command": command,
        }
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        result = None
    record = {
        "worker_record": True,
        "worker_schema": "solid-node-external-probe-v2",
        "status": process.returncode,
        "outer_wall_s": time.perf_counter() - started,
        "stdout": stdout[-16000:],
        "stderr": stderr[-16000:],
        "command": command,
        "cwd": str(REPO),
        "probe_path": str(script.relative_to(REPO)),
        "probe_sha256": sha256(script),
        "candidate_content_sha256": env.get(CANDIDATE_ENV),
        "result": result,
    }
    if result is None:
        record["worker_error"] = "external probe did not emit one JSON document"
        record["status"] = record["status"] or 1
    return record


def copy_fixture(target: Path) -> Path:
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"fixture target already exists: {target}")
    shutil.copytree(AUDIT / "fixtures", target, symlinks=True)
    reject_escaping_symlinks(target)
    if input_hashes(target) != input_hashes(AUDIT / "fixtures"):
        raise ValueError("fixed fixture copy differs from its input")
    return target


def summary(records: list[dict[str, object]]) -> dict[str, object]:
    values = [float(record["outer_wall_s"]) for record in records]
    return {
        "samples_s": values,
        "median_s": statistics.median(values),
        "min_s": min(values),
        "max_s": max(values),
        "runs": records,
    }


def planning_measurements(section: str) -> object:
    path = HERE / f"planning-head-baseline-{section}.json"
    return json.loads(path.read_text())["measurements"]


def planning_artifact_comparison(
    current: dict[str, object], baseline: dict[str, object], section: str
) -> dict[str, object]:
    candidate = current["planning_baseline_comparable_summary"]
    fields = {}
    for name in (
        "manifest_sha256", "stl_files", "stl_bytes", "pieces",
        "piece_instances",
    ):
        if name not in baseline:
            continue
        fields[name] = {
            "planning_baseline": baseline[name],
            "candidate": candidate[name],
            "equal": baseline[name] == candidate[name],
        }
    return {
        "planning_record": str(
            (HERE / f"planning-head-baseline-{section}.json").relative_to(REPO)
        ),
        "available_field_comparisons": fields,
        "all_available_fields_equal": all(item["equal"] for item in fields.values()),
        "full_stl_filename_sha256_baseline_available": False,
        "map_level_blindspot": PLANNING_MAP_BLINDSPOT,
    }


def startup_section(scratch: Path) -> dict[str, object]:
    project = copy_fixture(scratch / "startup-fixture")
    names = (
        "python_control", "cli_import", "parameters_import", "Solid2Node_import",
        "CadQueryNode_import", "test_import", "viewer_command", "models_command",
        "build_help",
    )
    return {
        name: summary([
            invoke(_worker_command("startup", "--snippet-name", name), project)
            for _ in range(5)
        ])
        for name in names
    }


def build_section(scratch: Path) -> list[dict[str, object]]:
    results = []
    baseline_index = {
        (item["backend"], item["count"], item["repeat"]): item
        for item in planning_measurements("build")
    }
    for backend, counts in (("solid", (1, 8, 24)), ("exact", (1, 8))):
        for count in counts:
            for repeat in range(3):
                project = copy_fixture(scratch / f"{backend}-{count}-{repeat}")
                argv = [
                    "build", f"bench.{backend}:Machine", "--set", f"count={count}"
                ]
                cold = invoke(_worker_command("cli", "--", *argv), project)
                post_cold = artifact_state(project)
                first_warm = invoke(_worker_command("cli", "--", *argv), project)
                settled = artifact_state(project)
                unchanged_worker = invoke(
                    _worker_command("cli", "--", *argv), project
                )
                unchanged = artifact_state(project)
                planning = baseline_index[(backend, count, repeat)]
                results.append({
                    "backend": backend,
                    "count": count,
                    "repeat": repeat,
                    "cold": cold,
                    "first_warm_v1_comparable": first_warm,
                    "unchanged_build": unchanged_worker,
                    "post_cold_artifacts": post_cold,
                    "post_first_warm_settled_artifacts": settled,
                    "post_third_unchanged_artifacts": unchanged,
                    "cold_to_first_warm_churn": artifact_churn(
                        post_cold, settled
                    ),
                    "complete_stl_map_equal": (
                        settled["stl_filename_sha256"]
                        == unchanged["stl_filename_sha256"]
                    ),
                    "manifest_byte_equal": settled["manifest"] == unchanged["manifest"],
                    "unchanged_churn": artifact_churn(settled, unchanged),
                    "planning_baseline_available_comparison": (
                        planning_artifact_comparison(
                            post_cold, planning["artifacts"], "build"
                        )
                    ),
                })
    return results


def batch_section(scratch: Path) -> list[dict[str, object]]:
    results = []
    planning = planning_measurements("batch")
    for repeat in range(3):
        actual = copy_fixture(scratch / f"actual-builder-{repeat}")
        actual_worker = invoke(
            _worker_command(
                "builder-detail", "--reference", "bench.solid:Machine",
                "--override", "count=24",
            ),
            actual,
            timeout=600,
        )
        actual_artifacts = artifact_state(actual)

        reference = copy_fixture(scratch / f"cli-reference-{repeat}")
        cli_worker = invoke(
            _worker_command(
                "cli", "--", "build", "bench.solid:Machine", "--set", "count=24"
            ),
            reference,
            timeout=600,
        )
        reference_artifacts = artifact_state(reference)
        results.append({
            "repeat": repeat,
            "candidate_actual_builder_generation": actual_worker,
            "current_cli_reference": cli_worker,
            "planning_baseline_comparison_label": (
                "planning-head-baseline batch worker was an isolated historical "
                "single-interpreter counterfactual; it is not relabelled as this fix"
            ),
            "actual_artifacts": actual_artifacts,
            "reference_artifacts": reference_artifacts,
            "complete_stl_map_equal": (
                actual_artifacts["stl_filename_sha256"]
                == reference_artifacts["stl_filename_sha256"]
            ),
            "manifest_byte_equal": (
                actual_artifacts["manifest"] == reference_artifacts["manifest"]
            ),
            "planning_baseline_available_comparison": {
                **planning_artifact_comparison(
                    actual_artifacts,
                    {"stl_files": planning[repeat]["stl_files"]},
                    "batch",
                ),
                "planning_baseline_batch_self_equivalence": (
                    planning[repeat]["stl_hashes_identical"]
                ),
            },
        })
    return results


def project_section(scratch: Path, catalogue: Path) -> list[dict[str, object]]:
    results = []
    baseline_index = {
        item["project"]: item for item in planning_measurements("projects")
    }
    for project_name in PROJECTS:
        runs = []
        for repeat in range(3):
            target, copy_record = copy_project(
                catalogue, project_name,
                scratch / f"{project_name.replace('/', '-')}-{repeat}",
            )
            settle = invoke(_worker_command("cli", "--", "build"), target, timeout=600)
            settled = artifact_state(target)
            warm = invoke(_worker_command("cli", "--", "build"), target, timeout=600)
            unchanged = artifact_state(target)
            runs.append({
                "repeat": repeat,
                "copy": copy_record,
                "settle": settle,
                "unchanged_build": warm,
                "settled_artifacts": settled,
                "unchanged_artifacts": unchanged,
                "complete_stl_map_equal": (
                    settled["stl_filename_sha256"]
                    == unchanged["stl_filename_sha256"]
                ),
                "manifest_byte_equal": settled["manifest"] == unchanged["manifest"],
                "unchanged_churn": artifact_churn(settled, unchanged),
                "planning_baseline_available_comparison": (
                    planning_artifact_comparison(
                        settled, baseline_index[project_name]["artifacts"],
                        "projects",
                    )
                ),
            })
        results.append({"project": project_name, "runs": runs})
    return results


def _manifest_names(project: Path) -> dict[str, object]:
    document = json.loads((project / "_build" / "viewer.json").read_text())
    names = []

    def walk(node):
        names.append(node.get("name"))
        for child in node.get("children", []):
            walk(child)

    walk(document["root"])
    return {"node_names": names, "pieces": document.get("pieces", [])}


def metadata_freshness_probe(scratch: Path) -> dict[str, object]:
    project = copy_fixture(scratch / "metadata-freshness")
    argv = [
        "build", "bench.solid:Machine", "--set", "count=1", "--set", "explicit=true"
    ]
    settle = invoke(_worker_command("cli", "--", *argv), project, timeout=600)
    before = artifact_state(project)
    before_semantics = _manifest_names(project)
    source = project / "bench" / "solid.py"
    old = source.read_text()
    needle = "name=f'parts-{i}' if self.explicit else None"
    replacement = "name=f'renamed-{i}' if self.explicit else None"
    if old.count(needle) != 1:
        raise ValueError("fixed metadata-only fixture edit no longer applies once")
    source.write_text(old.replace(needle, replacement))
    detail = invoke(
        _worker_command(
            "builder-detail", "--reference", "bench.solid:Machine",
            "--override", "count=1", "--override", "explicit=true",
        ),
        project,
        timeout=600,
    )
    after = artifact_state(project)
    after_semantics = _manifest_names(project)
    return {
        "settle": settle,
        "candidate_actual_builder_generation_after_metadata_edit": detail,
        "before": before,
        "after": after,
        "complete_stl_map_equal": (
            before["stl_filename_sha256"] == after["stl_filename_sha256"]
        ),
        "manifest_bytes_changed": before["manifest"] != after["manifest"],
        "before_semantics": before_semantics,
        "after_semantics": after_semantics,
        "current_metadata_visible": (
            "parts-0" in before_semantics["node_names"]
            and "renamed-0" in after_semantics["node_names"]
        ),
    }


def empirical_section(scratch: Path, catalogue: Path) -> dict[str, object]:
    projects = []
    for project_name in PROJECTS:
        target, copy_record = copy_project(
            catalogue, project_name,
            scratch / project_name.replace("/", "-"),
        )
        settle = invoke(_worker_command("cli", "--", "build"), target, timeout=600)
        settled = artifact_state(target)
        detail = invoke(
            _worker_command("builder-detail"), target, timeout=900, profile=True
        )
        after = artifact_state(target)
        projects.append({
            "project": project_name,
            "copy": copy_record,
            "settle": settle,
            "settled_artifacts": settled,
            "candidate_actual_builder_generation": detail,
            "after_artifacts": after,
            "complete_stl_map_equal": (
                settled["stl_filename_sha256"] == after["stl_filename_sha256"]
            ),
            "manifest_byte_equal": settled["manifest"] == after["manifest"],
            "detail_churn": artifact_churn(settled, after),
        })
    return {
        "projects": projects,
        "piece_metadata_freshness": metadata_freshness_probe(scratch),
    }


def algorithms_section(scratch: Path) -> dict[str, object]:
    runs = []
    for repeat in range(3):
        project = copy_fixture(scratch / f"algorithms-{repeat}")
        runs.append(invoke(_worker_command("algorithms"), project, timeout=600))
    return {"runs": runs}


def memory_section(scratch: Path) -> dict[str, object]:
    placement = []
    statics = []
    trajectory = []
    for repeat in range(3):
        placement.append(invoke_external(
            WP8, ["--mode", "bounded", "--counts", "1000", "4000", "8000"],
            timeout=900,
        ))
        statics.append(invoke_external(WP9, [], timeout=600))
        fixture = copy_fixture(scratch / f"trajectory-{repeat}")
        trajectory.append(invoke(
            _worker_command("trajectory", "--ticks", "4000"), fixture,
            timeout=600,
        ))
    return {
        "exact_placement": {
            "gc_policy": (
                "wp8_probe explicitly drops returned placements and calls gc.collect "
                "at each sample and after the working-set pass; VmRSS is current Linux "
                "process RSS and is not a universal per-shape allocation law"
            ),
            "runs": placement,
        },
        "sparse_statics_construction": {"runs": statics},
        "intentional_sim_trajectory_retention": {"runs": trajectory},
    }


SECTION_RUNNERS = {
    "startup": lambda scratch, catalogue: startup_section(scratch),
    "build": lambda scratch, catalogue: build_section(scratch),
    "batch": lambda scratch, catalogue: batch_section(scratch),
    "projects": lambda scratch, catalogue: project_section(scratch, catalogue),
    "empirical": lambda scratch, catalogue: empirical_section(scratch, catalogue),
    "algorithms": lambda scratch, catalogue: algorithms_section(scratch),
    "memory": lambda scratch, catalogue: memory_section(scratch),
}


def verify_section(section: str, measurements: object) -> None:
    validate_worker_tree(measurements)

    def verify_planning_comparison(comparison):
        if comparison["full_stl_filename_sha256_baseline_available"] is not False:
            raise ValueError("v1 baseline unexpectedly claims a retained full STL map")
        if not comparison["map_level_blindspot"]:
            raise ValueError("missing explicit planning-baseline map blind spot")
        fields = comparison["available_field_comparisons"]
        if not fields:
            raise ValueError("no available planning-baseline fields were compared")
        if comparison["all_available_fields_equal"] != all(
            item["equal"] for item in fields.values()
        ):
            raise ValueError("planning-baseline comparison summary is inconsistent")

    def verify_no_churn(churn, label):
        if churn["changed"]:
            raise ValueError(f"{label} rewrote or restamped unchanged artifacts")

    def verify_builder_detail(worker, *, require_no_scad_mutation=False):
        detail = worker["result"]
        counters = detail["counters"]
        if counters.get("root_assembly_computations") != 1:
            raise ValueError("actual Builder did not compute the root assembly once")
        consistency = detail["source_observation_counter_consistency"]
        if not consistency["equal"]:
            raise ValueError("source observation counters are inconsistent")
        if counters.get("piece_full_sha256_computations", 0) != counters.get(
            "piece_artifact_payload_reads", 0
        ):
            raise ValueError("piece digest and payload-read counters disagree")
        actual_scad_mutations = (
            counters.get("scad_actual_publish_writes", 0)
            + counters.get("scad_actual_restamps", 0)
        )
        if actual_scad_mutations > counters.get("atomic_text_write_calls", 0):
            raise ValueError("SCAD mutations exceed atomic writer invocations")
        if require_no_scad_mutation and actual_scad_mutations:
            raise ValueError("unchanged actual Builder mutated SCAD artifacts")

    if section == "build":
        for item in measurements:
            required = (
                "cold", "first_warm_v1_comparable", "unchanged_build",
                "post_cold_artifacts", "post_first_warm_settled_artifacts",
                "post_third_unchanged_artifacts", "cold_to_first_warm_churn",
                "unchanged_churn",
            )
            if any(name not in item for name in required):
                raise ValueError("build evidence lacks the explicit finite three-pass shape")
            if any(
                item[name].get("worker_record") is not True
                for name in (
                    "cold", "first_warm_v1_comparable", "unchanged_build"
                )
            ):
                raise ValueError("build evidence lacks one of three worker records")
            if not item["complete_stl_map_equal"] or not item["manifest_byte_equal"]:
                raise ValueError("build fixture changed output on unchanged input")
            verify_no_churn(item["unchanged_churn"], "unchanged build fixture")
            verify_planning_comparison(
                item["planning_baseline_available_comparison"]
            )
    elif section == "batch":
        for item in measurements:
            if not item["complete_stl_map_equal"] or not item["manifest_byte_equal"]:
                raise ValueError("actual Builder output differs from current CLI reference")
            verify_planning_comparison(
                item["planning_baseline_available_comparison"]
            )
            verify_builder_detail(item["candidate_actual_builder_generation"])
    elif section == "projects":
        for project in measurements:
            for run in project["runs"]:
                if not run["complete_stl_map_equal"] or not run["manifest_byte_equal"]:
                    raise ValueError(f"unchanged project output moved: {project['project']}")
                verify_no_churn(
                    run["unchanged_churn"],
                    f"unchanged project {project['project']}",
                )
                verify_planning_comparison(
                    run["planning_baseline_available_comparison"]
                )
    elif section == "empirical":
        for project in measurements["projects"]:
            detail = project["candidate_actual_builder_generation"]["result"]
            verify_builder_detail(
                project["candidate_actual_builder_generation"],
                require_no_scad_mutation=True,
            )
            bounds = detail["real_project_bounds"]
            if not bounds["set_equal"] or not bounds["order_equal"]:
                raise ValueError(f"broad-phase order mismatch: {project['project']}")
            if not project["complete_stl_map_equal"] or not project["manifest_byte_equal"]:
                raise ValueError(f"detail path changed settled output: {project['project']}")
            verify_no_churn(
                project["detail_churn"],
                f"unchanged actual Builder detail for {project['project']}",
            )
            flexible = detail.get("flexible")
            if flexible is not None and (
                flexible["interleaved_reads"] != 80
                or flexible["distinct_full_cache_keys_at_t_0_1"] != 3
                or flexible["faceted_geometry_constructions"] != 3
                or flexible["cache_high_water"] > flexible["cache_limit"]
            ):
                raise ValueError("V8 flexible working-set measurement failed")
        metadata = measurements["piece_metadata_freshness"]
        verify_builder_detail(
            metadata["candidate_actual_builder_generation_after_metadata_edit"]
        )
        if not (
            metadata["complete_stl_map_equal"]
            and metadata["manifest_bytes_changed"]
            and metadata["current_metadata_visible"]
        ):
            raise ValueError("piece metadata freshness measurement failed")
    elif section == "algorithms":
        for run in measurements["runs"]:
            result = run["result"]
            if not all(item["exact_legacy_x_order"]
                       for item in result["adaptive_sweep"]):
                raise ValueError("adaptive sweep differs from exact legacy X order")
            if not all(
                item["single_child_name_scans"] == 0
                and item["child_name_index_calls"] == 20
                and item["trajectory_entries"] == 20
                for item in result["naming_20_ticks"]
            ):
                raise ValueError("20-tick naming scan contract failed")
            if not all(
                item["production_sparse"]
                and item["failure_classification_equal"]
                and item["slack_allclose"]
                and item["coefficient_array_equal"]
                and item["target_array_equal"]
                and item["tolerance_array_equal"]
                for item in result["dense_sparse_equivalence"]
            ):
                raise ValueError("dense/sparse equivalence failed")
    elif section == "memory":
        for run in measurements["exact_placement"]["runs"]:
            result = run["result"]
            if result.get("mode") != "bounded":
                raise ValueError("exact placement evidence did not use bounded mode")
            samples = result["samples"]
            if [sample["count"] for sample in samples] != [1000, 4000, 8000]:
                raise ValueError("exact placement evidence used unexpected sample counts")
            if any(sample["cache_entries"] > result["cache_limit"]
                   for sample in samples):
                raise ValueError("exact placement cache exceeded its cap at a sample")
            working_set = result["working_set"]
            if (
                working_set["requests"] != 12
                or working_set["placement_constructions"] != 3
                or working_set["hits"] != 9
                or working_set["placement_constructions"] + working_set["hits"]
                != working_set["requests"]
                or working_set["cache_entries_after"] > result["cache_limit"]
            ):
                raise ValueError("exact placement working set did not reuse bounded entries")
        for run in measurements["sparse_statics_construction"]["runs"]:
            result = run["result"]
            if result["equality_nnz"] >= result["free_bodies"] ** 2:
                raise ValueError("representative statics matrix is not sparse")
        for run in measurements["intentional_sim_trajectory_retention"]["runs"]:
            result = run["result"]
            if (
                result["final_trajectory_entries"] != result["expected_entries"]
                or result["retained_driver_values"] != result["expected_driver_values"]
            ):
                raise ValueError("intentional Sim.trajectory retention changed")


def identity_file(label: str) -> Path:
    return HERE / f"{label}-candidate-identity.json"


def ensure_identity(label: str) -> dict[str, object]:
    current = candidate_identity()
    path = identity_file(label)
    if path.exists():
        recorded = json.loads(path.read_text())
        if recorded != current:
            raise ValueError(
                f"candidate differs from existing identity for label {label}; use a new label"
            )
    else:
        write_new_json(path, current)
    return current


def run_section(label: str, section: str, catalogue: Path | None) -> Path:
    output = HERE / f"{label}-{section}.json"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {output}")
    identity_before = ensure_identity(label)
    historical_before = historical_inventory()
    baseline_before = planning_baseline_inventory()
    originals_before = None
    if section in {"projects", "empirical"}:
        if catalogue is None:
            raise ValueError(f"{section} requires the exact project catalogue")
        originals_before = require_baseline_catalogue(catalogue)

    record: dict[str, object] = {
        "evidence_schema": "solid-node-performance-remediation-v2",
        "label": label,
        "section": section,
        "planning_head": PLANNING_HEAD,
        "candidate_identity_before": identity_before,
        "historical_inventory_before": historical_before,
        "planning_baseline_inventory_before": baseline_before,
        "original_catalogue_before": originals_before,
        "command": {
            "argv": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
            "cwd": str(REPO),
            "required_environment": {
                "PYTHONPATH": (
                    f"{REPO.resolve()}{os.pathsep}<verified-disposable-worker-cwd>"
                ),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        },
    }
    started = time.monotonic()
    failure = None
    try:
        with tempfile.TemporaryDirectory(
            prefix=f"solid-current-{label}-{section}-"
        ) as directory:
            previous_candidate = os.environ.get(CANDIDATE_ENV)
            os.environ[CANDIDATE_ENV] = identity_before["content_sha256"]
            try:
                measurement_environment = invoke(
                    _worker_command("environment"), Path(directory)
                )
                record["measurement_environment"] = measurement_environment
                validate_worker_tree(measurement_environment)
                require_worker_candidate(
                    measurement_environment, identity_before["content_sha256"]
                )
                measurements = SECTION_RUNNERS[section](Path(directory), catalogue)
                record["measurements"] = measurements
            finally:
                if previous_candidate is None:
                    os.environ.pop(CANDIDATE_ENV, None)
                else:
                    os.environ[CANDIDATE_ENV] = previous_candidate
        require_worker_candidate(measurements, identity_before["content_sha256"])
        verify_section(section, measurements)
    except BaseException:
        failure = sys.exc_info()
        record["runner_error"] = traceback.format_exc()
    finally:
        record["runner_wall_s"] = time.monotonic() - started
        try:
            identity_after = candidate_identity()
            record["candidate_identity_after"] = identity_after
            record["candidate_identity_unchanged"] = identity_before == identity_after
            if identity_before != identity_after:
                raise ValueError(f"candidate identity changed during {section}")
            record["historical_inventory_after"] = historical_inventory()
            record["planning_baseline_inventory_after"] = planning_baseline_inventory()
            if originals_before is not None:
                originals_after = catalogue_snapshot(catalogue)
                record["original_catalogue_after"] = originals_after
                record["original_catalogue_unchanged"] = (
                    originals_before == originals_after
                )
                record["original_catalogue_matches_planning_baseline"] = (
                    originals_after == require_baseline_catalogue(catalogue)
                )
                if originals_before != originals_after:
                    raise ValueError(f"original catalogue changed during {section}")
        except BaseException:
            if failure is None:
                failure = sys.exc_info()
            record["postflight_error"] = traceback.format_exc()
        write_new_json(output, record)
    if failure is not None:
        _, error, tb = failure
        raise error.with_traceback(tb)
    return output


def evidence_inventory(label: str) -> Path:
    output = HERE / f"{label}-evidence-inventory.json"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {output}")
    entries = []
    for path in sorted(HERE.glob(f"{label}-*")):
        if path == output or not path.is_file():
            continue
        if path.is_symlink():
            raise ValueError(f"evidence file may not be a symlink: {path}")
        entries.append({
            "path": str(path.relative_to(REPO)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    record = {
        "evidence_inventory_schema": "solid-node-performance-evidence-v2",
        "label": label,
        "candidate_content_sha256": ensure_identity(label)["content_sha256"],
        "entry_count": len(entries),
        "entries": entries,
    }
    write_new_json(output, record)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--section", choices=SECTIONS)
    selection.add_argument("--all", action="store_true")
    selection.add_argument("--inventory-evidence", action="store_true")
    parser.add_argument("--label", required=True)
    parser.add_argument("--catalogue", type=Path)
    args = parser.parse_args()
    label = validate_label(args.label)
    catalogue = args.catalogue.resolve() if args.catalogue else None
    chosen = SECTIONS if args.all else (() if args.inventory_evidence
                                        else (args.section,))
    if any(section in {"projects", "empirical"} for section in chosen):
        if catalogue is None:
            parser.error("project sections require --catalogue")
        if catalogue != EXPECTED_CATALOGUE.resolve():
            parser.error(f"catalogue must be exactly {EXPECTED_CATALOGUE}")

    outputs = []
    for section in chosen:
        print(f"current-candidate probe: {label}/{section}", flush=True)
        outputs.append(str(run_section(label, section, catalogue)))
    if args.all or args.inventory_evidence:
        outputs.append(str(evidence_inventory(label)))
    print(json.dumps({"outputs": outputs}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
