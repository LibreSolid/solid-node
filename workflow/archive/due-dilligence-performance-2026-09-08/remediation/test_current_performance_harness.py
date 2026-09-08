#!/usr/bin/env python3
"""Fast, non-CAD sanity tests for the v2 measurement harness."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import call, patch

import current_performance_common as common
import current_performance_worker as worker
import run_current_performance_probe as runner


class LabelTest(unittest.TestCase):

    def test_safe_labels_are_single_components(self):
        self.assertEqual(common.validate_label("current-candidate-01"),
                         "current-candidate-01")
        for value in ("../escape", "a/b", ".", "UPPER", "a.", "", "a" * 65):
            with self.subTest(value=value), self.assertRaises(ValueError):
                common.validate_label(value)


class NoOverwriteTest(unittest.TestCase):

    def test_atomic_writer_refuses_an_existing_evidence_file(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(common, "HERE", Path(directory)):
            target = Path(directory) / "record.json"
            common.write_new(target, b"first")
            with self.assertRaises(FileExistsError):
                common.write_new(target, b"second")
            self.assertEqual(target.read_bytes(), b"first")


class CandidateIdentityTest(unittest.TestCase):

    def test_candidate_and_immutable_baseline_heads_are_distinctly_attributed(self):
        self.assertEqual(
            common.PLANNING_HEAD,
            "2ca4b9f06835d1133b6ad00eceecdee6e29b714c",
        )
        inventory = common.planning_baseline_inventory()
        self.assertEqual(
            inventory["planning_baseline_head"],
            "4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c",
        )
        self.assertEqual(inventory["candidate_planning_head"], common.PLANNING_HEAD)
        self.assertTrue(inventory["heads_distinct"])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Harness Test"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "harness@example.invalid"],
                       cwd=self.repo, check=True)
        (self.repo / "solid_node").mkdir()
        (self.repo / "tests").mkdir()
        (self.repo / "solid_node" / "tracked.py").write_text("old\n")
        (self.repo / "tests" / "deleted.py").write_text("present\n")
        subprocess.run(["git", "add", "solid_node", "tests"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "base"],
                       cwd=self.repo, check=True)
        self.head = common.git(self.repo, "rev-parse", "HEAD")

    def test_manifest_hashes_modified_untracked_and_deleted_content(self):
        (self.repo / "solid_node" / "tracked.py").write_text("new\n")
        (self.repo / "tests" / "deleted.py").unlink()
        (self.repo / "tests" / "untracked.py").write_text("added\n")
        paths = {
            "solid_node/tracked.py", "tests/deleted.py", "tests/untracked.py"
        }
        first = common.candidate_identity(
            self.repo, expected_head=self.head, paths=paths
        )
        kinds = {entry["path"]: entry["kind"] for entry in first["entries"]}
        self.assertEqual(kinds, {
            "solid_node/tracked.py": "file",
            "tests/deleted.py": "deleted",
            "tests/untracked.py": "file",
        })
        (self.repo / "solid_node" / "tracked.py").write_text("newer\n")
        second = common.candidate_identity(
            self.repo, expected_head=self.head, paths=paths
        )
        self.assertNotEqual(first["content_sha256"], second["content_sha256"])

    def test_generated_json_is_excluded_but_probe_python_is_included(self):
        remediation = (
            self.repo / "workflow" / "due-dilligence-performance" / "remediation"
        )
        remediation.mkdir(parents=True)
        (remediation / "probe.py").write_text("pass\n")
        (remediation / "sample-section.json").write_text("{}\n")
        selected = common.candidate_path_set(self.repo)
        self.assertIn(
            "workflow/due-dilligence-performance/remediation/probe.py", selected
        )
        self.assertNotIn(
            "workflow/due-dilligence-performance/remediation/sample-section.json",
            selected,
        )


class WorkerValidationTest(unittest.TestCase):

    def test_absolute_worker_imports_disposable_cwd_and_framework_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            project = root / "project"
            scripts.mkdir()
            project.mkdir()
            (project / "fixture_local.py").write_text("VALUE = 'fixture-cwd'\n")
            worker_script = scripts / "worker.py"
            worker_script.write_text(
                "import json\n"
                "from pathlib import Path\n"
                "import fixture_local\n"
                "import solid_node\n"
                f"print({runner.MARKER!r} + json.dumps({{\n"
                "    'worker_record': True,\n"
                "    'status': 0,\n"
                "    'result': {\n"
                "        'fixture': fixture_local.VALUE,\n"
                "        'framework': solid_node.__name__,\n"
                "        'framework_origin': str(Path(solid_node.__file__).resolve()),\n"
                "    },\n"
                "}))\n"
            )
            record = runner.invoke(
                [sys.executable, str(worker_script)], project, timeout=30
            )
        self.assertEqual(common.validate_worker_tree(record), 1)
        self.assertEqual(record["pythonpath_entries"], [
            str(common.REPO.resolve()), str(project.resolve()),
        ])
        self.assertEqual(
            record["effective_pythonpath"],
            os.pathsep.join(record["pythonpath_entries"]),
        )
        self.assertEqual(record["result"], {
            "fixture": "fixture-cwd",
            "framework": "solid_node",
            "framework_origin": str(
                (common.REPO / "solid_node" / "__init__.py").resolve()
            ),
        })

    def test_worker_cwd_rejects_framework_and_original_project_scopes(self):
        for path in (
            common.REPO,
            common.REPO / "solid_node",
            common.EXPECTED_CATALOGUE,
            common.EXPECTED_CATALOGUE / common.PROJECTS[0],
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                runner.verified_worker_cwd(path)

    def planning_comparison(self):
        return runner.planning_artifact_comparison(
            {
                "planning_baseline_comparable_summary": {
                    "manifest_sha256": "same",
                    "stl_files": 1,
                    "stl_bytes": 10,
                    "pieces": 1,
                    "piece_instances": 1,
                }
            },
            {"manifest_sha256": "same", "stl_files": 1},
            "build",
        )

    def memory_measurements(self, samples, working_set):
        return {
            "exact_placement": {
                "gc_policy": "qualified test policy",
                "runs": [{
                    "worker_record": True,
                    "status": 0,
                    "result": {
                        "mode": "bounded",
                        "cache_limit": 512,
                        "samples": samples,
                        "working_set": working_set,
                    },
                }],
            },
            "sparse_statics_construction": {
                "runs": [{
                    "worker_record": True,
                    "status": 0,
                    "result": {"equality_nnz": 10, "free_bodies": 10},
                }],
            },
            "intentional_sim_trajectory_retention": {
                "runs": [{
                    "worker_record": True,
                    "status": 0,
                    "result": {
                        "final_trajectory_entries": 4,
                        "expected_entries": 4,
                        "retained_driver_values": 4,
                        "expected_driver_values": 4,
                    },
                }],
            },
        }

    def valid_build_measurement(self, unchanged_churn):
        successful_worker = {"worker_record": True, "status": 0}
        return {
            "cold": successful_worker,
            "first_warm_v1_comparable": successful_worker,
            "unchanged_build": successful_worker,
            "post_cold_artifacts": {},
            "post_first_warm_settled_artifacts": {},
            "post_third_unchanged_artifacts": {},
            "cold_to_first_warm_churn": {
                "changed": [{"path": "root.scad", "kind": "changed"}],
            },
            "complete_stl_map_equal": True,
            "manifest_byte_equal": True,
            "unchanged_churn": unchanged_churn,
            "planning_baseline_available_comparison": self.planning_comparison(),
        }

    def test_unchanged_build_rejects_byte_identical_file_churn(self):
        measurements = [self.valid_build_measurement({
                "changed": [{"path": "part.scad", "kind": "changed"}],
        })]
        with self.assertRaises(ValueError):
            runner.verify_section("build", measurements)

    def test_build_allows_first_settlement_churn_when_third_pass_is_clean(self):
        runner.verify_section(
            "build", [self.valid_build_measurement({"changed": []})]
        )

    def test_build_rejects_missing_explicit_third_unchanged_pass(self):
        measurements = [{
            "complete_stl_map_equal": True,
            "manifest_byte_equal": True,
            "unchanged_churn": {"changed": []},
            "planning_baseline_available_comparison": self.planning_comparison(),
        }]
        with self.assertRaises(ValueError):
            runner.verify_section("build", measurements)

    def test_placement_rejects_an_early_over_cap_sample(self):
        measurements = self.memory_measurements(
            [
                {"count": 1000, "cache_entries": 513},
                {"count": 4000, "cache_entries": 512},
                {"count": 8000, "cache_entries": 512},
            ],
            {"requests": 12, "placement_constructions": 3, "hits": 9,
             "cache_entries_after": 512},
        )
        with self.assertRaises(ValueError):
            runner.verify_section("memory", measurements)

    def test_placement_rejects_a_zero_reuse_working_set(self):
        measurements = self.memory_measurements(
            [
                {"count": 1000, "cache_entries": 512},
                {"count": 4000, "cache_entries": 512},
                {"count": 8000, "cache_entries": 512},
            ],
            {"requests": 12, "placement_constructions": 12, "hits": 0,
             "cache_entries_after": 512},
        )
        with self.assertRaises(ValueError):
            runner.verify_section("memory", measurements)

    def test_root_assembly_counter_recognizes_only_explicit_false(self):
        class TruthMustNotBeTested:
            _assembled = object()

            def __bool__(self):
                raise AssertionError("truth evaluation is forbidden")

        self.assertTrue(worker.root_assembly_will_compute(
            type("Fresh", (), {"_assembled": False})()
        ))
        self.assertFalse(worker.root_assembly_will_compute(
            type("Done", (), {"_assembled": True})()
        ))
        self.assertFalse(worker.root_assembly_will_compute(TruthMustNotBeTested()))

    def test_planning_comparison_reports_available_fields_and_map_blindspot(self):
        current = {
            "planning_baseline_comparable_summary": {
                "manifest_sha256": "same",
                "stl_files": 24,
                "stl_bytes": 100,
                "pieces": 24,
                "piece_instances": 24,
            }
        }
        comparison = runner.planning_artifact_comparison(
            current,
            {"manifest_sha256": "same", "stl_files": 24, "stl_bytes": 99},
            "build",
        )
        self.assertTrue(
            comparison["available_field_comparisons"]["manifest_sha256"]["equal"]
        )
        self.assertFalse(
            comparison["available_field_comparisons"]["stl_bytes"]["equal"]
        )
        self.assertFalse(comparison["all_available_fields_equal"])
        self.assertFalse(
            comparison["full_stl_filename_sha256_baseline_available"]
        )
        self.assertIn("no complete filename-to-SHA-256 map",
                      comparison["map_level_blindspot"])

    def test_nested_nonzero_timeout_and_error_are_rejected(self):
        failures = (
            {"nested": [{"worker_record": True, "status": 7}]},
            {"nested": {"worker_record": True, "status": 0, "timeout_s": 1}},
            {"nested": {"worker_record": True, "status": 0,
                        "worker_error": "hidden"}},
            {"nested": {"status": 3}},
        )
        for value in failures:
            with self.subTest(value=value), self.assertRaises(ValueError):
                common.validate_worker_tree(value)
        self.assertEqual(common.validate_worker_tree({
            "nested": [{"worker_record": True, "status": 0}]
        }), 1)

    def test_python_control_worker_emits_one_success_record(self):
        with tempfile.TemporaryDirectory() as directory:
            record = runner.invoke(
                runner._worker_command(
                    "startup", "--snippet-name", "python_control"
                ),
                Path(directory),
                timeout=30,
            )
        self.assertEqual(common.validate_worker_tree(record), 1)
        self.assertEqual(record["result"], {"snippet": "python_control"})
        self.assertNotIn("packages", record["sample_context"])

    def test_full_environment_is_a_separate_untimed_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            record = runner.invoke(
                runner._worker_command("environment"), Path(directory), timeout=30
            )
        self.assertEqual(common.validate_worker_tree(record), 1)
        self.assertIn("packages", record["result"])
        self.assertIn("load_average", record["result"])

    def test_external_timeout_escalates_from_term_to_kill(self):
        class HungProcess:
            pid = 17891
            returncode = None

            def __init__(self):
                self.communications = 0

            def communicate(self, timeout=None):
                self.communications += 1
                if self.communications <= 2:
                    raise subprocess.TimeoutExpired(["probe"], timeout)
                self.returncode = -9
                return "", ""

        process = HungProcess()
        with patch.object(runner.subprocess, "Popen", return_value=process), \
                patch.object(runner.os, "killpg") as killpg:
            record = runner.invoke_external(Path("probe.py"), [], timeout=0.01)
        self.assertEqual(process.communications, 3)
        self.assertEqual(
            killpg.call_args_list,
            [call(process.pid, runner.signal.SIGTERM),
             call(process.pid, runner.signal.SIGKILL)],
        )
        self.assertEqual(record["timeout_s"], 0.01)
        self.assertEqual(record["status"], -9)

    def test_failed_gate_preserves_the_raw_measurement_record(self):
        identity = {
            "identity_schema": "solid-node-uncommitted-candidate-v2",
            "planning_head": common.PLANNING_HEAD,
            "content_sha256": "candidate",
            "entry_count": 0,
            "entries": [],
        }
        environment = {
            "worker_record": True,
            "worker_schema": "solid-node-performance-worker-v2",
            "candidate_content_sha256": "candidate",
            "status": 0,
        }
        rejected = {
            "worker_record": True,
            "worker_schema": "solid-node-performance-worker-v2",
            "candidate_content_sha256": "candidate",
            "status": 7,
            "diagnostic": "retained",
        }
        inventory = {"all_match": True}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(common, "HERE", Path(directory)), \
                patch.object(runner, "HERE", Path(directory)), \
                patch.object(runner, "ensure_identity", return_value=identity), \
                patch.object(runner, "candidate_identity", return_value=identity), \
                patch.object(runner, "historical_inventory", return_value=inventory), \
                patch.object(
                    runner, "planning_baseline_inventory", return_value=inventory
                ), \
                patch.object(runner, "invoke", return_value=environment), \
                patch.dict(
                    runner.SECTION_RUNNERS,
                    {"startup": lambda scratch, catalogue: rejected},
                ):
            with self.assertRaises(ValueError):
                runner.run_section("failed-gate", "startup", None)
            saved = json.loads(
                (Path(directory) / "failed-gate-startup.json").read_text()
            )
        self.assertEqual(saved["measurement_environment"], environment)
        self.assertEqual(saved["measurements"], rejected)
        self.assertEqual(saved["measurements"]["diagnostic"], "retained")
        self.assertIn("runner_error", saved)


class DisposablePathTest(unittest.TestCase):

    def test_source_catalogue_targets_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            catalogue = Path(directory) / "projects"
            source = catalogue / "group" / "project"
            source.mkdir(parents=True)
            for target in (source, source / "nested", catalogue / "other"):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    common.require_disposable_target(target, source, catalogue)

    def test_escaping_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "copy"
            root.mkdir()
            (root / "outside").symlink_to(Path(directory).parent)
            with self.assertRaises(ValueError):
                common.reject_escaping_symlinks(root)


if __name__ == "__main__":
    unittest.main()
