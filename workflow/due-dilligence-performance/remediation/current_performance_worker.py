#!/usr/bin/env python3
"""Fresh-process workers for the v2 current-candidate performance harness.

Every result is emitted behind one machine-readable marker.  Exceptions are
recorded and make this process non-zero so the outer runner can reject both the
exit status and a nested error record.  Expensive framework/CAD imports remain
inside the selected worker mode, preserving startup measurements.
"""

from __future__ import annotations

import argparse
import cProfile
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import pstats
import resource
import sys
import time
import traceback

from current_performance_common import (
    CANDIDATE_ENV, REPO, artifact_churn, artifact_state,
)


MARKER = "CURRENT_PERFORMANCE_RESULT="


def rss_kib() -> int:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    raise RuntimeError("VmRSS was not present in /proc/self/status")


def profile_text(profiler: cProfile.Profile) -> str:
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs().sort_stats("cumulative").print_stats(45)
    stats.sort_stats("tottime").print_stats(25)
    return stream.getvalue()


def root_assembly_will_compute(node) -> bool:
    """Recognize the framework's explicit pre-assembly state without truth tests."""
    return getattr(node, "_assembled", False) is False


def environment() -> dict[str, object]:
    packages = {}
    for name in (
        "solid-node", "cadquery", "cadquery-ocp", "build123d", "trimesh",
        "manifold3d", "molejo", "numpy", "scipy",
    ):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "packages": packages,
        "affinity_cpus": sorted(os.sched_getaffinity(0)),
        "load_average": os.getloadavg(),
        "cpu": next(
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("model name")
        ),
        "thread_environment": {
            key: os.environ.get(key)
            for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        },
    }


def sample_context() -> dict[str, object]:
    """Cheap per-sample clock/load context; full provenance is an untimed worker."""
    return {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "load_average": os.getloadavg(),
    }


STARTUP_SNIPPETS = {
    "python_control": "pass",
    "cli_import": "import solid_node.cli",
    "parameters_import": "import solid_node.parameters",
    "Solid2Node_import": "from solid_node.node import Solid2Node",
    "CadQueryNode_import": "from solid_node.node import CadQueryNode",
    "test_import": "import solid_node.test",
    "viewer_command": (
        "import sys; sys.argv=['solid','viewer']; "
        "from solid_node.cli import manage; manage()"
    ),
    "models_command": (
        "import sys; sys.argv=['solid','models','--json']; "
        "from solid_node.cli import manage; manage()"
    ),
    "build_help": (
        "import sys; sys.argv=['solid','build','-h']; "
        "from solid_node.cli import manage; manage()"
    ),
}


def startup(name: str) -> dict[str, object]:
    try:
        snippet = STARTUP_SNIPPETS[name]
    except KeyError:
        raise ValueError(f"unknown fixed startup snippet: {name}") from None
    namespace = {"__name__": "__current_performance_probe__"}
    try:
        exec(snippet, namespace)
    except SystemExit as error:
        if error.code not in (None, 0):
            raise
    return {"snippet": name}


def cli(argv: list[str]) -> dict[str, object]:
    import solid_node.manager.build as build_module

    real_process = build_module.Process
    children = []

    def counted(*arguments, **keywords):
        process = real_process(*arguments, **keywords)
        children.append(process)
        return process

    build_module.Process = counted
    try:
        from solid_node.cli import manage
        sys.argv = ["solid", *argv]
        try:
            manage()
            exit_status = 0
        except SystemExit as error:
            exit_status = int(error.code or 0)
    finally:
        build_module.Process = real_process
    if exit_status:
        raise RuntimeError(f"solid CLI exited {exit_status}: {argv!r}")
    return {
        "argv": argv,
        "cli_status": exit_status,
        "builder_processes": len(children),
        "builder_exitcodes": [process.exitcode for process in children],
    }


def _legacy_x_candidates(bounds):
    """Planning-head X sweep, retained only as an ordering oracle."""
    import numpy as np

    order = sorted(
        range(len(bounds)),
        key=lambda index: (bounds[index][0][0], bounds[index][1][0], index),
    )
    active = []
    for current in order:
        minimum = bounds[current][0][0]
        active = [index for index in active if bounds[index][1][0] >= minimum]
        for candidate in active:
            first, second = bounds[candidate], bounds[current]
            if np.any(first[1] < second[0]) or np.any(second[1] < first[0]):
                continue
            yield min(candidate, current), max(candidate, current)
        active.append(current)


def _intersection_record(action) -> dict[str, object]:
    samples = []
    result = None
    for _ in range(3):
        started = time.perf_counter()
        result = action()
        samples.append(time.perf_counter() - started)
    return {
        "samples_s": samples,
        "median_s": sorted(samples)[1],
        "result": {
            "is_empty": bool(result.is_empty),
            "volume": float(result.volume),
            "exact": bool(result.exact),
        },
    }


def _flexible_detail(root, nodes) -> dict[str, object] | None:
    from unittest.mock import patch

    import solid_node.test as checks

    springs = [node for node in nodes if type(node).__name__ == "ValveSpring"]
    valves = [node for node in nodes if type(node).__name__ == "Valve"]
    if not springs or not valves:
        return None
    spring, valve = springs[0], valves[0]
    policies = []
    for instant in (0.0, 0.1, 0.2, 0.3):
        root.set_keyframe(instant)
        instant_record = {"t": instant}
        for policy_name in ("exact", "faceted"):
            checks.set_comparison_policy(
                checks.resolve_comparison_policy(policy_name)
            )
            instant_record[policy_name] = _intersection_record(
                lambda: checks._intersection_stats(spring, valve)
            )
        policies.append(instant_record)

    checks.set_comparison_policy(checks.resolve_comparison_policy("faceted"))
    root.set_keyframe(0.1)
    full_keys = [candidate._faceted_cache_snapshot()[0] for candidate in springs]
    checks._flexible_manifold_cache.clear()
    construction_count = 0
    original_admitted = checks._admitted

    def admitted(*arguments, **keywords):
        nonlocal construction_count
        construction_count += 1
        return original_admitted(*arguments, **keywords)

    volumes = []
    high_water = 0
    with patch.object(checks, "_admitted", new=admitted):
        started = time.perf_counter()
        for _ in range(5):
            for candidate in springs:
                manifold, _ = checks._flexible_manifold(candidate)
                volumes.append(float(manifold.volume()))
                high_water = max(high_water, len(checks._flexible_manifold_cache))
        elapsed = time.perf_counter() - started
    return {
        "spring_count": len(springs),
        "distinct_full_cache_keys_at_t_0_1": len(set(full_keys)),
        "interleaved_reads": len(volumes),
        "faceted_geometry_constructions": construction_count,
        "cache_limit": checks._FLEXIBLE_MANIFOLD_CACHE_LIMIT,
        "cache_high_water": high_water,
        "elapsed_s": elapsed,
        "volume_sequence": volumes,
        "separately_selected_policy_verdicts": policies,
        "verdict_cache_claim": "none; every flexible comparison invoked its selected kernel",
    }


def builder_detail(reference: str | None, overrides: list[str]) -> dict[str, object]:
    """Measure the actual Builder lifecycle in this fresh worker interpreter."""
    import asyncio
    from collections import Counter, defaultdict
    from contextlib import ExitStack
    from unittest.mock import patch

    import solid_node.core.builder as builder_module
    from solid_node.core.builder import Builder, BuildOutcome
    from solid_node.core.loader import select_model
    import solid_node.core.pieces as pieces
    import solid_node.currency as currency
    import solid_node.node.base as base
    import solid_node.node.fusion as fusion
    import solid_node.source_generation as source_generation

    counters = Counter()
    paths: dict[str, Counter] = defaultdict(Counter)
    phases = []
    fusion_order = []
    root_holder = {}
    before = artifact_state(Path.cwd())

    real_load = builder_module.load_node
    real_generate_stl = Builder.generate_stl
    real_generate_scad = base.AbstractBaseNode.generate_scad
    real_write_text = base._atomic_write_text
    real_currency_record = currency.record
    real_currency_publish = currency.publish
    real_currency_restamp = currency.restamp
    real_observe = source_generation._observe_real_path
    real_digest = source_generation._coherent_real_source_digest
    real_census_realpath = source_generation.SourceCensus.realpath
    real_phase_exit = source_generation.SourcePhase.__exit__
    real_fact_read = pieces._read_fact_record
    real_fact_publish = pieces._publish_fact_record
    real_fact_digest = pieces._digest_bytes
    real_fact_decode = pieces._geometry_facts_from_bytes
    real_fuse = fusion.fuse_shapes
    real_snapshot = Builder._write_viewer_snapshot
    text_write_depth = 0

    def counted_load(*arguments, **keywords):
        counters["load_node_calls"] += 1
        if keywords.get("generation") is None:
            raise AssertionError(
                "builder-detail reached load_node without the production source generation"
            )
        node = real_load(*arguments, **keywords)
        root_holder["node"] = node
        original_assemble = node.assemble
        original_render = node.render

        def counted_assemble(*inner_args, **inner_kwargs):
            counters["root_assemble_invocations"] += 1
            if root_assembly_will_compute(node):
                counters["root_assembly_computations"] += 1
            return original_assemble(*inner_args, **inner_kwargs)

        def counted_render(*inner_args, **inner_kwargs):
            counters["root_structural_render_calls"] += 1
            return original_render(*inner_args, **inner_kwargs)

        node.assemble = counted_assemble
        node.render = counted_render
        return node

    async def counted_generate_stl(self):
        counters["builder_artifact_passes"] += 1
        result = await real_generate_stl(self)
        counters[f"builder_artifact_outcome_{result.name}"] += 1
        return result

    def counted_generate_scad(self):
        counters["node_generate_scad_invocations"] += 1
        paths["generate_scad_invocation_paths"][
            os.path.realpath(self.scad_file)
        ] += 1
        return real_generate_scad(self)

    def counted_write_text(path, *arguments, **keywords):
        nonlocal text_write_depth
        counters["atomic_text_write_calls"] += 1
        paths["atomic_text_write_call_paths"][os.path.realpath(path)] += 1
        text_write_depth += 1
        try:
            return real_write_text(path, *arguments, **keywords)
        finally:
            text_write_depth -= 1

    def counted_publish(temporary, artifact, *arguments, **keywords):
        if text_write_depth:
            counters["scad_actual_publish_writes"] += 1
            paths["scad_actual_publish_paths"][os.path.realpath(artifact)] += 1
        return real_currency_publish(temporary, artifact, *arguments, **keywords)

    def counted_restamp(artifact, *arguments, **keywords):
        if text_write_depth:
            counters["scad_actual_restamps"] += 1
            paths["scad_actual_restamp_paths"][os.path.realpath(artifact)] += 1
        return real_currency_restamp(artifact, *arguments, **keywords)

    def counted_record(path, *arguments, **keywords):
        counters["currency_record_calls"] += 1
        paths["currency_record_artifacts"][os.path.realpath(path)] += 1
        return real_currency_record(path, *arguments, **keywords)

    def counted_observe(real):
        phase = source_generation.current_phase()
        label = phase.label if phase is not None else "generation_or_load_boundary"
        counters["source_observations"] += 1
        paths[f"source_observations:{label}"][real] += 1
        return real_observe(real)

    def counted_digest(real):
        counters["source_full_digest_reads"] += 1
        paths["source_full_digest_paths"][real] += 1
        return real_digest(real)

    def counted_realpath(self, path):
        counters["census_realpath_requests"] += 1
        paths["census_realpath_spellings"][os.path.abspath(os.fspath(path))] += 1
        return real_census_realpath(self, path)

    def counted_phase_exit(self, exc_type, exc, traceback_value):
        try:
            return real_phase_exit(self, exc_type, exc, traceback_value)
        finally:
            phases.append({
                "label": self.label,
                "observed_distinct_paths": len(self.census._observations),
                "content_digest_paths": len(self.census._digests),
                "content_byte_paths": len(self.census._bytes),
                "canonical_spellings": len(self.census._canonical),
            })

    def counted_fact_read(path, observation):
        counters["piece_fact_record_reads"] += 1
        result = real_fact_read(path, observation)
        counters["piece_fact_record_hits" if result is not None
                 else "piece_fact_record_misses"] += 1
        return result

    def counted_fact_publish(*arguments, **keywords):
        counters["piece_fact_record_writes"] += 1
        return real_fact_publish(*arguments, **keywords)

    def counted_fact_digest(data):
        counters["piece_full_sha256_computations"] += 1
        counters["piece_artifact_payload_reads"] += 1
        return real_fact_digest(data)

    def counted_fact_decode(*arguments, **keywords):
        counters["piece_mesh_decodes"] += 1
        return real_fact_decode(*arguments, **keywords)

    def counted_fuse(first, second, first_name, second_name):
        fusion_order.append([first_name, second_name])
        return real_fuse(first, second, first_name, second_name)

    def counted_snapshot(self):
        counters["viewer_snapshot_calls"] += 1
        return real_snapshot(self)

    selection = select_model(reference)
    selection.anchor()
    with ExitStack() as stack:
        stack.enter_context(patch.object(builder_module, "load_node", new=counted_load))
        stack.enter_context(patch.object(Builder, "generate_stl", new=counted_generate_stl))
        stack.enter_context(patch.object(base.AbstractBaseNode, "generate_scad", new=counted_generate_scad))
        stack.enter_context(patch.object(base, "_atomic_write_text", new=counted_write_text))
        stack.enter_context(patch.object(currency, "record", new=counted_record))
        stack.enter_context(patch.object(currency, "publish", new=counted_publish))
        stack.enter_context(patch.object(currency, "restamp", new=counted_restamp))
        stack.enter_context(patch.object(source_generation, "_observe_real_path", new=counted_observe))
        stack.enter_context(patch.object(source_generation, "_coherent_real_source_digest", new=counted_digest))
        stack.enter_context(patch.object(source_generation.SourceCensus, "realpath", new=counted_realpath))
        stack.enter_context(patch.object(source_generation.SourcePhase, "__exit__", new=counted_phase_exit))
        stack.enter_context(patch.object(pieces, "_read_fact_record", new=counted_fact_read))
        stack.enter_context(patch.object(pieces, "_publish_fact_record", new=counted_fact_publish))
        stack.enter_context(patch.object(pieces, "_digest_bytes", new=counted_fact_digest))
        stack.enter_context(patch.object(pieces, "_geometry_facts_from_bytes", new=counted_fact_decode))
        stack.enter_context(patch.object(fusion, "fuse_shapes", new=counted_fuse))
        stack.enter_context(patch.object(Builder, "_write_viewer_snapshot", new=counted_snapshot))
        started = time.perf_counter()
        builder = Builder(
            selection.reference, watch=False, lifecycle=True, overrides=overrides
        )
        outcome = asyncio.run(builder._start())
        elapsed = time.perf_counter() - started
    if outcome is not BuildOutcome.CURRENT:
        raise RuntimeError(f"actual Builder ended with {outcome.name}")
    node = root_holder["node"]
    after = artifact_state(Path.cwd())

    nodes = []

    def walk(current):
        nodes.append(current)
        for child in current.children:
            walk(child)

    walk(node)
    from solid_node.node.base import _compose_world_matrix, _topmost_rigid_nodes
    import solid_node.test as checks

    solids = list(_topmost_rigid_nodes(node))
    node.set_keyframe(0)
    bounds = [
        checks._world_bounds(
            checks._cached_local_bounds(solid.stl_file),
            _compose_world_matrix(solid),
        )
        for solid in solids
    ]
    actual_pairs = list(checks._bounds_candidates(bounds))
    legacy_pairs = list(_legacy_x_candidates(bounds))
    pressures = [checks._axis_order_and_pressure(bounds, axis)[1]
                 for axis in range(3)] if bounds else [0, 0, 0]
    flexible = _flexible_detail(node, nodes)
    source_observation_path_calls = sum(
        sum(counter.values()) for name, counter in paths.items()
        if name.startswith("source_observations:")
    )
    if source_observation_path_calls != counters["source_observations"]:
        raise AssertionError(
            "source observation global/per-phase path counters disagree: "
            f"{counters['source_observations']} != {source_observation_path_calls}"
        )

    return {
        "path_kind": "actual Builder._start lifecycle in a fresh worker; no fabricated generation",
        "reference": selection.reference,
        "overrides": overrides,
        "build_outcome": outcome.name,
        "elapsed_s": elapsed,
        "counters": dict(sorted(counters.items())),
        "path_counters": {
            name: {
                "calls": sum(counter.values()),
                "distinct": len(counter),
                "per_path": dict(sorted(counter.items())),
            }
            for name, counter in sorted(paths.items())
        },
        "source_phases": phases,
        "source_observation_counter_consistency": {
            "global_calls": counters["source_observations"],
            "per_phase_path_calls": source_observation_path_calls,
            "equal": True,
        },
        "exact_fusion_order": fusion_order,
        "tree": {
            "nodes": len(nodes),
            "selected_rigid_instances": len(solids),
            "distinct_selected_artifacts": len({solid.stl_file for solid in solids}),
            "source_closure_entries": sum(len(current.files) for current in nodes),
            "distinct_sources": len(set().union(*(current.files for current in nodes))),
        },
        "real_project_bounds": {
            "count": len(bounds),
            "axis_pressures": pressures,
            "selected_axis": min(range(3), key=lambda axis: (pressures[axis], axis)),
            "candidate_count": len(actual_pairs),
            "candidate_pairs": actual_pairs,
            "exact_legacy_x_order": legacy_pairs,
            "set_equal": set(actual_pairs) == set(legacy_pairs),
            "order_equal": actual_pairs == legacy_pairs,
        },
        "flexible": flexible,
        "artifact_before": before,
        "artifact_after": after,
        "artifact_churn": artifact_churn(before, after),
        "manifest_byte_equal": before["manifest"] == after["manifest"],
        "stl_filename_sha256_equal": (
            before["stl_filename_sha256"] == after["stl_filename_sha256"]
        ),
    }


def algorithm_probes() -> dict[str, object]:
    from unittest.mock import patch

    import numpy as np
    from scipy import sparse
    import solid_node.test as framework

    sweep = []
    for count in (128, 256, 512, 1024):
        for separated_axis in (0, 1, 2):
            bounds = []
            for index in range(count):
                low = np.zeros(3)
                high = np.ones(3)
                low[separated_axis] = 3 * index
                high[separated_axis] = 3 * index + 1
                bounds.append((low, high))
            legacy = list(_legacy_x_candidates(bounds))
            checks = 0
            real_disjoint = framework._boxes_disjoint

            def counted_disjoint(*arguments, **keywords):
                nonlocal checks
                checks += 1
                return real_disjoint(*arguments, **keywords)

            started = time.perf_counter()
            with patch.object(framework, "_boxes_disjoint", new=counted_disjoint):
                actual = list(framework._bounds_candidates(bounds))
            elapsed = time.perf_counter() - started
            pressures = [framework._axis_order_and_pressure(bounds, axis)[1]
                         for axis in range(3)]
            sweep.append({
                "count": count,
                "separated_axis": separated_axis,
                "axis_pressures": pressures,
                "selected_axis": min(range(3), key=lambda axis: (pressures[axis], axis)),
                "candidate_count": len(actual),
                "full_aabb_checks": checks,
                "elapsed_s": elapsed,
                "exact_legacy_x_order": actual == legacy,
            })

    from solid_node.node.base import AbstractBaseNode
    from solid_node.simulation import Sim
    from bench.solid import Driven

    naming = []
    real_index = AbstractBaseNode._child_name_index
    real_single = AbstractBaseNode._attr_name_for
    for count in (128, 512, 2048):
        index_calls = 0
        single_calls = 0

        def counted_index(self):
            nonlocal index_calls
            index_calls += 1
            return real_index(self)

        def counted_single(self, child):
            nonlocal single_calls
            single_calls += 1
            return real_single(self, child)

        with patch.object(AbstractBaseNode, "_child_name_index", new=counted_index), \
                patch.object(AbstractBaseNode, "_attr_name_for", new=counted_single):
            node = Driven(count=count, distinct=False, explicit=False)
            sim = Sim(node, dt=0.01)
            index_calls = single_calls = 0
            started = time.perf_counter()
            sim.run(0.2)
            elapsed = time.perf_counter() - started
        naming.append({
            "count": count,
            "ticks": 20,
            "elapsed_s": elapsed,
            "child_name_index_calls": index_calls,
            "single_child_name_scans": single_calls,
            "trajectory_entries": len(sim.trajectory),
            "first_last_names": [node.parts[0].name, node.parts[-1].name],
        })

    # The dense reference is test-only planning-HEAD code.  Production still
    # supplies the sparse program to HiGHS; candidate identity covers both.
    from tests.test_sparse_statics import (
        _body, _contact, _dense_reference, _production_result,
    )
    statics = []
    cases = [
        (
            "feasible",
            [_body("free"), _body("anchor", anchored=True)],
            [_contact((0, 0, 0), (0, 0, 1), 0, 1)],
            (),
        ),
        (
            "force-failure",
            [_body("free"), _body("anchor", anchored=True)],
            [_contact((0, 0, 0), (1, 0, 0), 0, 1)],
            (),
        ),
        (
            "declared-wrench",
            [_body("free"), _body("anchor", anchored=True)],
            [],
            ((0, 1),),
        ),
    ]
    gravity = np.array([0.0, 0.0, -1.0])
    for name, bodies, contacts, declared in cases:
        dense = _dense_reference(bodies, contacts, declared, gravity)
        actual = _production_result(bodies, contacts, declared, gravity)
        actual_coefficients = (
            actual.coefficients.toarray()
            if sparse.issparse(actual.coefficients) else actual.coefficients
        )
        statics.append({
            "case": name,
            "production_sparse": sparse.issparse(actual.equality),
            "failure_classification_equal": actual.failures == dense.failures,
            "objective_delta": float(actual.objective - dense.objective),
            "slack_allclose": bool(np.allclose(
                actual.slack, dense.slack, rtol=1e-10, atol=1e-12
            )),
            "coefficient_array_equal": bool(np.array_equal(
                actual_coefficients, dense.coefficients
            )),
            "target_array_equal": bool(np.array_equal(actual.target, dense.target)),
            "tolerance_array_equal": bool(np.array_equal(
                actual.tolerance, dense.tolerance
            )),
            "dense_failures": dense.failures,
            "production_failures": actual.failures,
        })
    return {
        "adaptive_sweep": sweep,
        "naming_20_ticks": naming,
        "dense_sparse_equivalence": statics,
    }


def trajectory_probe(ticks: int) -> dict[str, object]:
    from bench.solid import Driven
    from solid_node.simulation import Sim

    node = Driven(count=1, distinct=False, explicit=True)
    sim = Sim(node, dt=0.001)
    samples = []
    chunk = ticks // 4
    started = time.perf_counter()
    for target in (chunk, 2 * chunk, 3 * chunk, ticks):
        sim.run((target - sim.tick) * sim.dt)
        samples.append({
            "ticks": sim.tick,
            "trajectory_entries": len(sim.trajectory),
            "retained_driver_values": sum(len(values) for _, values in sim.trajectory),
            "rss_kib": rss_kib(),
        })
    driver_count = len(sim.drivers)
    return {
        "ticks": ticks,
        "driver_count": driver_count,
        "samples": samples,
        "final_trajectory_entries": len(sim.trajectory),
        "expected_entries": ticks,
        "retained_driver_values": sum(len(values) for _, values in sim.trajectory),
        "expected_driver_values": ticks * driver_count,
        "elapsed_s": time.perf_counter() - started,
        "disposition": (
            "intentional Sim.trajectory retention proportional to ticks x drivers; "
            "measured for preservation, not presented as a fix"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", required=True,
        choices=(
            "environment", "startup", "cli", "builder-detail", "algorithms",
            "trajectory",
        ),
    )
    parser.add_argument("--snippet-name", choices=tuple(STARTUP_SNIPPETS))
    parser.add_argument("--reference")
    parser.add_argument("--override", action="append", default=[])
    parser.add_argument("--ticks", type=int, default=4000)
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.argv[:1] == ["--"]:
        args.argv = args.argv[1:]

    record: dict[str, object] = {
        "worker_record": True,
        "worker_schema": "solid-node-performance-worker-v2",
        "mode": args.mode,
        "pid": os.getpid(),
        "candidate_content_sha256": os.environ.get(CANDIDATE_ENV),
        "sample_context": sample_context(),
    }
    profiler = cProfile.Profile() if args.profile else None
    started = time.perf_counter()
    status = 0
    try:
        if profiler:
            profiler.enable()
        if args.mode == "environment":
            record["result"] = environment()
        elif args.mode == "startup":
            if args.snippet_name is None:
                raise ValueError("startup requires --snippet-name")
            record["result"] = startup(args.snippet_name)
        elif args.mode == "cli":
            record["result"] = cli(args.argv)
        elif args.mode == "builder-detail":
            record["result"] = builder_detail(args.reference, args.override)
        elif args.mode == "algorithms":
            record["result"] = algorithm_probes()
        elif args.mode == "trajectory":
            if args.ticks < 4 or args.ticks % 4:
                raise ValueError("--ticks must be a positive multiple of four")
            record["result"] = trajectory_probe(args.ticks)
    except BaseException:
        status = 1
        record["worker_error"] = traceback.format_exc()
    finally:
        if profiler:
            profiler.disable()
            record["profile"] = profile_text(profiler)
        record["elapsed_s"] = time.perf_counter() - started
        record["peak_self_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        record["peak_child_rss_kib"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        record["current_rss_kib"] = rss_kib()
        record["module_count"] = len(sys.modules)
        record["heavy_imports"] = [
            name for name in (
                "trimesh", "cadquery", "OCP", "build123d", "molejo", "solid_node.test"
            ) if name in sys.modules
        ]
        record["status"] = status
        print(MARKER + json.dumps(record, sort_keys=True), flush=True)
    return status


if __name__ == "__main__":
    sys.exit(main())
