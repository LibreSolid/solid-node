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
    load_test, load_node, import_module_from_path, find_class,
    AmbiguousNodeError,
)
from solid_node.node.base import AbstractBaseNode


class StopTestRun(Exception):
    """Internal control-flow signal raised to unwind out of the test run
    when --failfast is set and a test fails."""


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

    def handle(self, args):
        path = self.resolve_path(args.path)
        self.node = self.build_node(path)
        self.test_case = load_test(path)
        if self.test_case:
            self.test_case.set_node(self.node)
        self.failfast = args.failfast
        self.run_tests()
        if self.num_failed:
            sys.exit(1)

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

    def build_node(self, path, time=0):
        self.ensure_node_class(path)
        node = load_node(path)
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

    def run_tests(self):
        start_time = time.time()

        try:
            self.run_class_tests(self.node, self.node)
            if self.test_case:
                self.run_class_tests(self.test_case, self.node)
        except StopTestRun:
            pass

        end_time = time.time()
        total_time = end_time - start_time
        sys.stdout.write(f"\nRan {self.num_tests} tests in {total_time:.2f} seconds: {self.num_passed} passed, {self.num_failed} failed\n")

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
