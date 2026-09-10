# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import bdb
import time
import traceback
from termcolor import colored
from solid_node.core.loader import (
    ProjectManifestError, load_tests, load_node, read_project, resolve_node,
    select_model,
    import_module_from_path, find_class,
    AmbiguousNodeError, project_root, _defined_classes,
)
from solid_node.core.builder import project_build_lock
from solid_node.node.base import AbstractBaseNode
from solid_node.test import (ComparisonPolicy, DEFAULT_PLACEMENT_QUANTUM,
                             resolve_comparison_policy, set_comparison_policy)


class StopTestRun(Exception):
    """Internal control-flow signal raised to unwind out of the test run
    when --failfast is set and a test fails."""


def _reset_placement_cache_for_run():
    """Clear exact placement retention without importing the exact kernel.

    A fresh CLI process has no placement cache. This only matters when a
    managed run is established in an interpreter that already used exact
    geometry; keep the faceted-only path from loading CadQuery just to clear
    an absent cache.
    """
    exact = sys.modules.get('solid_node.exact')
    if exact is not None:
        exact._reset_placement_cache()


class Test:
    """Nodes may implement tests by inheriting solid_node.test.TestCaseMixin
    and creating test methods starting with test_.
    Run all tests from a node."""

    needs_node = True

    def __init__(self):
        self.num_tests = 0
        self.num_passed = 0
        self.num_failed = 0
        self.failfast = False

    def add_arguments(self, parser):
        parser.add_argument('--failfast',
                            action='store_true',
                            help='Stop the test run on the first error.')
        kernel = parser.add_mutually_exclusive_group()
        kernel.add_argument(
            '--exact', dest='kernel', action='store_const', const='exact',
            help='Compare exact parts on the boundary-representation '
                 'kernel (the default, and what SOLID_TEST_KERNEL=exact '
                 'selects).')
        kernel.add_argument(
            '--faceted', dest='kernel', action='store_const', const='faceted',
            help='Compare every pair on the parts\' meshes, at tessellation '
                 'precision: the fast development loop, selected for a '
                 'checkout by SOLID_TEST_KERNEL=faceted in its .env.')
        parser.add_argument(
            '--volume-epsilon', type=float, default=None, metavar='MM3',
            help='Under --faceted, report an intersection of at most this '
                 'volume as empty (default SOLID_TEST_VOLUME_EPSILON, else '
                 '0). The exact kernel refuses it.')
        parser.add_argument(
            '--placement-quantum', type=float, default=None, metavar='MM',
            help='Merge two relative placements into one verdict-memo '
                 'question when they differ by less than this (default '
                 'SOLID_TEST_PLACEMENT_QUANTUM, else '
                 f'{DEFAULT_PLACEMENT_QUANTUM:g}). Accepted by both '
                 'kernels; 0 restores the exact-bytes key.')
        parser.add_argument('--all', action='store_true',
                            help='Test every model the project declares, '
                                 'as one run.')

    def handle(self, args):
        try:
            self.policy = resolve_comparison_policy(
                getattr(args, 'kernel', None),
                getattr(args, 'volume_epsilon', None),
                getattr(args, 'placement_quantum', None))
        except ValueError as error:
            self.fail(str(error))
        set_comparison_policy(self.policy)
        _reset_placement_cache_for_run()
        if self.policy.kernel == 'faceted':
            sys.stdout.write(
                'Comparing on the faceted kernel (volume epsilon '
                f'{self.policy.volume_epsilon:g} mm³): verdicts are at '
                'tessellation precision, not exact.\n')
        self.failfast = args.failfast
        self.overrides = list(getattr(args, 'set', None) or [])
        if getattr(args, 'all', False):
            selections = self.select_all(args.path)
        else:
            path = self.resolve_path(args.path) if args.path else args.path
            try:
                selection = select_model(path)
            except ProjectManifestError as error:
                self.fail(str(error))
            selection.anchor()
            path = selection.reference
            try:
                klass, node_path, root = resolve_node(path)
                selections = [(klass, node_path, path, None)]
            except AmbiguousNodeError:
                # A bare file is the one reference deliberately allowed to
                # name several nodes when testing: the ones its companion
                # test cases declare, in the file's order, and no other. A
                # sub-assembly nobody tests is never built -- it may not
                # build alone. With nothing declared, every class it
                # defines, as before.
                root = project_root(path)
                node_path = os.path.realpath(path)
                module = import_module_from_path(node_path, root)
                candidates = _defined_classes(
                    node_path, module, AbstractBaseNode)
                declared = []
                for case_class in load_tests(node_path, root):
                    node_class = getattr(case_class, 'node', None)
                    if node_class is None:
                        self.fail(f"{case_class.__name__} must declare node; "
                                  "candidates: "
                                  + ', '.join(name for name, _ in candidates))
                    declared.append(node_class)
                selections = [(klass, node_path, f'{node_path}:{name}', None)
                              for name, klass in candidates
                              if not declared or klass in declared]
        # One run covers every selected node, and reports once: a file
        # reference naming several nodes is still a single test run, not one
        # run per node -- and neither is a walk over every declared model.
        start_time = time.time()
        try:
            for klass, node_path, reference, model in selections:
                if model is not None:
                    select_model(model.name).anchor()
                    root = read_project().root
                    if klass is None:
                        # The model did not resolve; that is its failure,
                        # counted once, and the walk goes on.
                        self.record_model_failure(model.name, node_path)
                        continue
                try:
                    self.node = self.build_node(
                        reference, fatal=model is None)
                except Exception as error:
                    if model is None:
                        raise
                    self.record_model_failure(model.name, error)
                    continue
                self.test_case = None
                self.test_cases = []
                candidates = _defined_classes(
                    node_path, import_module_from_path(node_path, root),
                    AbstractBaseNode)
                for case_class in load_tests(node_path, root):
                    declared = getattr(case_class, 'node', None)
                    if declared is None and len(candidates) != 1:
                        self.fail(f"{case_class.__name__} must declare node; candidates: "
                                  + ', '.join(name for name, _ in candidates))
                    if declared is not None and declared is not klass:
                        continue
                    case = case_class()
                    case.set_node(self.node)
                    self.test_cases.append(case)
                self.run_selection()
        except StopTestRun:
            pass
        self.report(time.time() - start_time)
        if self.num_failed:
            sys.exit(1)

    def select_all(self, path):
        """Every declared model as a selection. A model whose reference does
        not resolve is carried as `(None, <error>, reference, model)`, so
        the run can count it as a failure without stopping."""
        if path:
            self.fail('--all takes no reference')
        try:
            project = read_project()
        except ProjectManifestError as error:
            self.fail(str(error))
        if not project.named:
            self.fail(f'{project.manifest} declares no models; --all walks '
                      f'a [tool.solid-node.models] table')
        selections = []
        for model in project.models:
            select_model(model.name).anchor()
            try:
                klass, node_path, _ = resolve_node(model.reference)
            except Exception as error:
                selections.append((None, str(error), model.reference, model))
                continue
            selections.append((klass, node_path, model.reference, model))
        return selections

    def resolve_path(self, path):
        """Users and agents routinely hand `solid test` the TEST file
        instead of the node file it exercises: `root/test_gear.py`
        instead of `root/gear.py`, or `root/test.py` instead of
        `root/__init__.py`. Map it back to the node file -- the mirror
        image of loader.load_test's node->test mapping -- so the run
        proceeds exactly as if the node path had been given. Only
        `solid test` has an unambiguous reason to do this; `develop`
        and `snapshot` are left alone.
        """
        directory, filename = os.path.split(path)
        if filename == 'test.py':
            mapped_name = '__init__.py'
        elif filename.startswith('test_'):
            mapped_name = filename[len('test_'):]
        else:
            return path

        node_path = os.path.join(directory, mapped_name)
        if not os.path.exists(node_path):
            self.fail(f"No such node file: {node_path} (mapped from test path {path})")
        return node_path

    def record_model_failure(self, name, error):
        """Count one declared model that could not reach its tests."""
        self.num_tests += 1
        self.num_failed += 1
        if isinstance(error, Exception):
            reason = f'{type(error).__name__}: {error}'
        else:
            reason = str(error)
        sys.stderr.write(f"Error: model {name}: {reason}\n")
        if self.failfast:
            raise StopTestRun

    def build_node(self, path, time=0, fatal=True):
        try:
            node = load_node(path, overrides=getattr(self, 'overrides', None))
        except Exception as error:
            if fatal:
                self.fail(str(error))
            raise
        with project_build_lock():
            node.set_keyframe(time)
            rendered = node.render()
            node.assemble()
            node.build_stls()
        return node

    def ensure_node_class(self, path):
        """load_node blindly instantiates whatever class the loader
        finds for `path`; if the module defines no AbstractBaseNode
        subclass, the loader returns None and instantiating it raises
        a bare `TypeError: 'NoneType' object is not callable`. Check
        first so the failure is a clear, one-line, nonzero-exit error
        naming the path -- never that traceback."""
        real_path = os.path.realpath(path)
        module = import_module_from_path(real_path)
        try:
            klass = find_class(real_path, module, AbstractBaseNode)
        except AmbiguousNodeError as e:
            self.fail(str(e))
            return
        if klass is None:
            self.fail(f"No node class found in {path}")

    def fail(self, message):
        sys.stderr.write(f"Error: {message}\n")
        sys.exit(1)

    def run_selection(self):
        """Run one selected node: its own test methods, then every companion
        case bound to it. StopTestRun propagates, so --failfast stops the whole
        run and not merely the current node."""
        self.run_class_tests(self.node, self.node)
        for test_case in getattr(self, 'test_cases',
                                 [self.test_case] if self.test_case else []):
            self.test_case = test_case
            self.run_class_tests(test_case, self.node)

    def report(self, total_time):
        summary = (f"Ran {self.num_tests} tests in {total_time:.2f} seconds: "
                   f"{self.num_passed} passed, {self.num_failed} failed")
        policy = getattr(self, 'policy', ComparisonPolicy('exact', 0.0))
        notes = []
        if policy.kernel == 'faceted':
            # A green fast run must never read as an exact one in a log.
            notes.append(f"faceted kernel, volume epsilon "
                        f"{policy.volume_epsilon:g} mm³")
        if policy.placement_quantum != DEFAULT_PLACEMENT_QUANTUM:
            # The default run's output must stay byte-for-byte what it is
            # today (ADR-090); only a non-default quantum is worth a line.
            notes.append(f"placement quantum {policy.placement_quantum:g} mm")
        if notes:
            summary += f" ({', '.join(notes)})"
        sys.stdout.write(f"\n{summary}\n")

    def run_tests(self):
        start_time = time.time()
        try:
            self.run_selection()
        except StopTestRun:
            pass
        self.report(time.time() - start_time)

    # node is kept as argument to be used for recursion into children later
    def run_class_tests(self, klass, node):
        if hasattr(klass, "setUpClass"):
            klass.setUpClass()

        for method_name in dir(klass):
            if method_name.startswith("test_"):
                method = getattr(klass, method_name)
                if callable(method):
                    self.num_tests += 1
                    self.run_test(klass, method_name, method, node)

        if hasattr(klass, "tearDownClass"):
            klass.tearDownClass()

    def run_test(self, klass, name, method, node):
        node._testMethodName = name
        self.save_children_checkpoints(node)

        try:
            if hasattr(self.test_case, "setUp"):
                self.test_case.setUp()
            try:
                class_name = klass.__name__
            except AttributeError:
                class_name = klass.__class__.__name__
            sys.stdout.write(f"Running {class_name}.{name}")
            sys.stdout.flush()
            step_pass = 0
            step_fail = 0
            error = None
            instants = getattr(method, 'testing_instants', [0])
            for instant in instants:
                try:
                    node.set_keyframe(instant)
                    method()
                    step_pass += 1
                    dot_color = 'green'
                except bdb.BdbQuit:
                    print("Developer quit!")
                    return
                except Exception as e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    error = (
                        exc_type,
                        exc_value,
                        "".join(traceback.format_exception(
                            exc_type,
                            exc_value,
                            exc_traceback
                        ))
                    )
                    step_fail += 1
                    dot_color = 'red'
                sys.stdout.write(colored('.', dot_color))
                sys.stdout.flush()
                # Every instant starts from clean children: a leaked
                # operation must not poison the following instants.
                self.restore_children_checkpoints(node)
                if self.failfast and dot_color == 'red':
                    break
            if not step_fail:
                sys.stdout.write(colored(" passed\n", "green"))
                self.num_passed += 1
            else:
                sys.stdout.write(colored('FAIL!\n', 'red'))
                print(error[2])
                self.num_failed += 1
                if self.failfast:
                    raise StopTestRun()
        finally:
            if hasattr(self.test_case, "tearDown"):
                self.test_case.tearDown()
            self.restore_children_checkpoints(node)

    def save_children_checkpoints(self, node):
        """Snapshot each child's exact operations list. The snapshots
        are held by the runner itself, so a test calling
        save_checkpoint() on a node cannot clobber the restore point;
        and they restore by content, so an operation INSERTED anywhere
        in the list (not just appended) is reverted too."""
        self._children_operations = {
            child: list(child.operations) for child in node.children
        }

    def restore_children_checkpoints(self, node):
        for child, operations in getattr(
                self, '_children_operations', {}).items():
            child.operations[:] = list(operations)
