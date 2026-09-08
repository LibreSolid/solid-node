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

from trimesh.creation import box

from solid_node.core.builder import Builder, get_errors_file
from .test_build_lock import lock_is_held

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

VANISHING_JSCAD_PIPE = '''\
import os
from solid_node.node import JScadNode


class SimplePipe(JScadNode):
    jscad_source = "shape.js"

    def __init__(self):
        super().__init__()
        os.remove(self.jscad_source)
'''

VANISHING_SIBLING_JSCAD_MODEL = '''\
import os
from solid_node.node import JScadNode


class SiblingAsset(JScadNode):
    jscad_source = "../assets/shape.js"

    def __init__(self):
        super().__init__()
        os.remove(self.jscad_source)
        os.rmdir(os.path.dirname(self.jscad_source))
'''


def _run_builder(project_root, build_dir, is_reload,
                 path='flat_project/simple_pipe.py'):
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
    Builder(path, is_reload=is_reload).start()


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
        # A scratch project is a real project: the framework finds its root
        # and its model through the manifest, not through the working
        # directory.
        with open(os.path.join(self.project_root, 'pyproject.toml'), 'w') as stream:
            stream.write('[tool.solid-node]\n'
                         'model = "flat_project.simple_pipe:SimplePipe"\n')


        self.build_dir = os.path.join(self.tmp_root, '_build')
        self.errors_file = os.path.join(self.build_dir, 'errors.json')

        self._procs = []

    def tearDown(self):
        for proc in self._procs:
            if proc.is_alive():
                proc.terminate()
            proc.join(timeout=10)

    def spawn(self, is_reload, path='flat_project/simple_pipe.py'):
        proc = multiprocessing.Process(
            target=_run_builder,
            args=(self.project_root, self.build_dir, is_reload, path),
        )
        proc.start()
        self._procs.append(proc)
        return proc

    def write_pipe(self, content):
        with open(self.simple_pipe, 'w') as f:
            f.write(content)

    def write_jscad_source(self):
        with open(os.path.join(os.path.dirname(self.simple_pipe), 'shape.js'),
                  'w') as source:
            source.write('return cube({size: 1});\n')

    def write_sibling_jscad_source(self):
        assets = os.path.join(self.project_root, 'assets')
        os.makedirs(assets, exist_ok=True)
        source_path = os.path.join(assets, 'shape.js')
        with open(source_path, 'w') as source:
            source.write('return cube({size: 1});\n')
        return source_path

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
        # cleanly, clear the error state, build the complete model, and retain
        # that one source generation while it watches.  It no longer exits
        # after an intermediate artifact pass merely to reload the same tree.
        second = self.spawn(is_reload=True)
        viewer = os.path.join(self.build_dir, 'viewer.json')
        self.assertTrue(self.wait_until(
            lambda: os.path.exists(viewer)
            and not os.path.exists(self.errors_file), timeout=60))
        self.assertTrue(second.is_alive(),
                        'completed generation exited instead of watching')
        self.assertFalse(lock_is_held(self.build_dir),
                         'completed generation watches under the build lock')

        # A relevant repair/edit ends the retained generation. Builder.start
        # maps SOURCE_CHANGED to the legacy direct-call exit 0; Develop uses
        # lifecycle=True and observes the distinct outcome value instead.
        self.write_pipe(GOOD_SIMPLE_PIPE + '\n')
        second.join(timeout=15)
        self.assertFalse(second.is_alive())
        self.assertEqual(second.exitcode, 0)

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

    def test_missing_initial_foreign_source_reload_waits_for_repair(self):
        self.write_jscad_source()
        self.write_pipe(VANISHING_JSCAD_PIPE)

        proc = self.spawn(is_reload=True)
        self.assertTrue(self.wait_until(
            lambda: self.read_error() is not None, timeout=15),
            'initial source-census failure was not reported')
        self.assertTrue(proc.is_alive(),
                        'reload died instead of waiting for repair')
        self.assertFalse(lock_is_held(self.build_dir),
                         'reload recovery waited under the project lock')
        self.assertIn('FileNotFoundError', self.read_error()['error'])

        self.write_jscad_source()
        proc.join(timeout=15)
        self.assertFalse(proc.is_alive(),
                         'reload did not observe the foreign-source repair')
        self.assertEqual(proc.exitcode, 0)

    def test_missing_sibling_foreign_source_reload_waits_for_exact_repair(self):
        models = os.path.join(self.project_root, 'models')
        os.makedirs(models)
        with open(os.path.join(models, 'model.py'), 'w') as model:
            model.write(VANISHING_SIBLING_JSCAD_MODEL)
        self.write_sibling_jscad_source()

        proc = self.spawn(is_reload=True, path='models/model.py')
        self.assertTrue(self.wait_until(
            lambda: self.read_error() is not None, timeout=15),
            'sibling source-census failure was not reported')
        self.assertTrue(proc.is_alive(),
                        'reload died instead of waiting for sibling repair')
        self.assertFalse(lock_is_held(self.build_dir),
                         'sibling recovery waited under the project lock')

        # The nearest existing ancestor must be watched because construction
        # removed both the known foreign file and its parent.  That broader
        # subscription is transport only: unrelated foreign files and Python
        # outside the entry module's original broad-recovery subtree remain
        # irrelevant.
        assets = os.path.join(self.project_root, 'assets')
        os.makedirs(assets)
        with open(os.path.join(assets, 'unrelated.js'), 'w') as unrelated:
            unrelated.write('not a contributor\n')
        proc.join(timeout=1)
        self.assertTrue(proc.is_alive(),
                        'unrelated foreign repair ended the recovery wait')

        with open(os.path.join(assets, 'unrelated.py'), 'w') as unrelated:
            unrelated.write('not_a_project_import = True\n')
        proc.join(timeout=1)
        self.assertTrue(
            proc.is_alive(),
            'sibling Python edit widened the existing broad recovery area')

        repaired = os.path.join(assets, 'shape.js')
        with open(repaired, 'w') as source:
            source.write('return cube({size: 2});\n')
        proc.join(timeout=15)
        self.assertFalse(proc.is_alive(),
                         'reload did not observe the sibling source repair')
        self.assertEqual(proc.exitcode, 0)

    def test_missing_initial_foreign_source_startup_fails(self):
        self.write_jscad_source()
        self.write_pipe(VANISHING_JSCAD_PIPE)

        proc = self.spawn(is_reload=False)
        proc.join(timeout=15)

        self.assertFalse(proc.is_alive())
        self.assertNotEqual(proc.exitcode, 0)
        self.assertIsNotNone(self.read_error())


class ImportedStlWatchTest(TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='solid_node_stl_watch_test_')
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        package = os.path.join(self.root, 'parts')
        os.makedirs(package)
        with open(os.path.join(package, '__init__.py'), 'w') as stream:
            stream.write('')
        with open(os.path.join(package, 'bracket.py'), 'w') as stream:
            stream.write(
                'from solid_node.node import StlNode\n'
                'class Bracket(StlNode):\n'
                '    stl_source = "bracket.stl"\n')
        self.source = os.path.join(package, 'bracket.stl')
        box().export(self.source, file_type='stl')
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as stream:
            stream.write('[tool.solid-node]\n'
                         'model = "parts.bracket:Bracket"\n')
        self.build_dir = os.path.join(self.root, '_build')
        self.proc = None

    def tearDown(self):
        if self.proc is not None and self.proc.is_alive():
            self.proc.terminate()
        if self.proc is not None:
            self.proc.join(timeout=10)

    def wait_until(self, predicate, timeout=15, interval=0.1):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(interval)
        return predicate()

    def test_modifying_tracked_stl_ends_the_builder_watch(self):
        self.proc = multiprocessing.Process(
            target=_run_builder,
            args=(self.root, self.build_dir, False, 'parts/bracket.py'),
        )
        self.proc.start()

        snapshot = os.path.join(self.build_dir, 'viewer.json')
        self.assertTrue(self.wait_until(
            lambda: os.path.exists(snapshot) and self.proc.is_alive()),
            'builder never published and entered its watch')

        with open(self.source, 'ab') as stream:
            stream.write(b'\n')

        self.proc.join(timeout=5)
        self.assertFalse(
            self.proc.is_alive(),
            'builder ignored a modification to its tracked STL source')
        self.assertEqual(self.proc.exitcode, 0)
