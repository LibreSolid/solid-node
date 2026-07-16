# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Regression tests for improvements.md #7: a file saved in a
transiently broken state (module-level NameError, SyntaxError, ...)
while `solid develop` is watching used to leave the builder subprocess
hung forever -- no observer had been started yet to notice a later fix
-- instead of being surfaced like any other build failure.

These drive the real `Builder` (real watchdog Observer, real asyncio
event loop, real filesystem) in a child process, exactly like
`Develop.handle()` does in production: each attempt is a fresh
`multiprocessing.Process`, so `sys.exit()` inside `Builder._start()`
only ever ends that child, never the test process.
"""

import multiprocessing
import os
import shutil
import sys
import tempfile
import time
from unittest import TestCase

from solid_node.core.builder import Builder, get_errors_file

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAT_PROJECT = os.path.join(REPO_DIR, 'tests', 'flat_project')

GOOD_SIMPLE_PIPE = '''\
from solid_node.node import Solid2Node
from solid2 import cylinder


class SimplePipe(Solid2Node):

    def render(self):
        return cylinder(r=10, h=100) - cylinder(r=8, h=100)
'''

NAME_ERROR_SIMPLE_PIPE = '''\
from solid_node.node import Solid2Node
from solid2 import cylinder

this_name_is_never_defined_anywhere

class SimplePipe(Solid2Node):

    def render(self):
        return cylinder(r=10, h=100) - cylinder(r=8, h=100)
'''

SYNTAX_ERROR_SIMPLE_PIPE = '''\
from solid_node.node import Solid2Node
from solid2 import cylinder


class SimplePipe(Solid2Node):

    def render(self):
        return cylinder(r=10 h=100) - cylinder(r=8, h=100)
'''


def _run_builder(project_root, build_dir, is_reload):
    """Target for the child process: chdir into the scratch project
    root and run one Builder attempt, mirroring how Develop.handle()
    invokes Builder(self.path, is_reload=...).start() in production.

    solid_node.core.loader appends os.getcwd() to sys.path, but only
    the first time it is imported -- which already happened in the
    parent (pytest) process with the *real* cwd. This is a forked
    child (multiprocessing default on Linux), so that already-appended
    entry came along for the ride; chdir() alone would not make the
    scratch project's package importable, so put it on sys.path here
    explicitly too.
    """
    os.chdir(project_root)
    sys.path.insert(0, project_root)
    os.environ['SOLID_BUILD_DIR'] = build_dir
    Builder('flat_project/simple_pipe.py', is_reload=is_reload).start()


class BuilderReloadResilienceTest(TestCase):
    """TDD for #7: reload-time import errors must not take the whole
    develop process down with them."""

    def setUp(self):
        self.tmp_root = tempfile.mkdtemp(prefix='solid_node_builder_test_')
        self.addCleanup(shutil.rmtree, self.tmp_root, ignore_errors=True)

        self.project_root = self.tmp_root
        project_copy = os.path.join(self.project_root, 'flat_project')
        shutil.copytree(FLAT_PROJECT, project_copy,
                         ignore=shutil.ignore_patterns('__pycache__'))
        self.simple_pipe = os.path.join(project_copy, 'simple_pipe.py')

        self.build_dir = os.path.join(self.tmp_root, '_build')
        self.errors_file = os.path.join(self.build_dir, 'errors.json')

        self._procs = []

    def tearDown(self):
        for proc in self._procs:
            if proc.is_alive():
                proc.terminate()
            proc.join(timeout=10)

    def spawn(self, is_reload):
        proc = multiprocessing.Process(
            target=_run_builder,
            args=(self.project_root, self.build_dir, is_reload),
        )
        proc.start()
        self._procs.append(proc)
        return proc

    def write_pipe(self, content):
        with open(self.simple_pipe, 'w') as f:
            f.write(content)

    def wait_until(self, predicate, timeout=10, interval=0.1):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(interval)
        return predicate()

    def read_error(self):
        if not os.path.exists(self.errors_file):
            return None
        # Small retry in case we read mid-write.
        for _ in range(5):
            try:
                with open(self.errors_file) as f:
                    import json
                    return json.load(f)
            except (ValueError, json.JSONDecodeError):
                time.sleep(0.05)
        return None

    def _reload_survives_and_surfaces(self, broken_content, needle):
        self.write_pipe(broken_content)

        proc = self.spawn(is_reload=True)

        got_error = self.wait_until(
            lambda: self.read_error() is not None, timeout=15)
        self.assertTrue(got_error, "error was never written to errors.json")

        # The develop machinery must still be alive: it must NOT have
        # crashed or hung with nothing watching.
        self.assertTrue(proc.is_alive(),
                         "builder subprocess died instead of staying up "
                         "to watch for a fix")

        error = self.read_error()
        self.assertIn(needle, error['error'])

        # Now fix the file: the still-alive process must notice and
        # exit cleanly (its job is only to detect the fix and let
        # Develop's loop respawn a fresh attempt).
        self.write_pipe(GOOD_SIMPLE_PIPE)

        proc.join(timeout=15)
        self.assertFalse(proc.is_alive(),
                          "builder subprocess did not recover after the "
                          "file was fixed")
        self.assertEqual(proc.exitcode, 0)

    def test_name_error_reload_stays_alive_and_surfaces_error(self):
        self._reload_survives_and_surfaces(NAME_ERROR_SIMPLE_PIPE, 'NameError')

    def test_syntax_error_reload_stays_alive_and_surfaces_error(self):
        self._reload_survives_and_surfaces(SYNTAX_ERROR_SIMPLE_PIPE, 'SyntaxError')

    def test_recovery_reload_clears_error_and_builds(self):
        # Start broken so there is an error to clear.
        self.write_pipe(NAME_ERROR_SIMPLE_PIPE)
        first = self.spawn(is_reload=True)
        self.assertTrue(self.wait_until(lambda: self.read_error() is not None,
                                         timeout=15))

        self.write_pipe(GOOD_SIMPLE_PIPE)
        first.join(timeout=15)
        self.assertEqual(first.exitcode, 0)

        # A fresh reload attempt against the now-fixed file must load
        # cleanly, clear the error state, and actually build the model.
        second = self.spawn(is_reload=True)
        second.join(timeout=60)

        self.assertEqual(second.exitcode, 0)
        self.assertFalse(os.path.exists(self.errors_file),
                          "error state was not cleared after recovery")

    def test_startup_failure_does_not_hang_forever(self):
        # The very first attempt (is_reload=False) for an
        # already-broken project must exit promptly with a clear
        # error -- it must NOT survive/keep watching like a reload
        # would, and it must NOT hang forever either.
        self.write_pipe(NAME_ERROR_SIMPLE_PIPE)

        proc = self.spawn(is_reload=False)
        proc.join(timeout=15)

        self.assertFalse(proc.is_alive(),
                          "startup attempt hung instead of exiting cleanly")
        self.assertNotEqual(proc.exitcode, 0)
