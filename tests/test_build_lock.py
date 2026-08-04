# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Process-level proof for the project build lock."""

import fcntl
import glob
import json
import multiprocessing
import os
import shutil
import signal
import sys
import tempfile
import time
from argparse import Namespace
from unittest import TestCase
from unittest.mock import Mock, patch

from solid_node.core.builder import (
    get_build_dir, get_build_lock_path, project_build_lock,
)


REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAT_PROJECT = os.path.join(REPO_DIR, 'tests', 'flat_project')


def _hold_lock(build_dir, ready, release):
    with project_build_lock(build_dir):
        ready.set()
        release.wait(10)


def _acquire_lock(build_dir, acquired):
    with project_build_lock(build_dir):
        acquired.set()


def _idle(release):
    release.wait(10)


def lock_is_held(build_dir):
    """Whether anything holds the project build lock right now.

    `flock` conflicts are per open file description, so a fresh descriptor
    answers this honestly even from the process holding the lock.
    """
    path = get_build_lock_path(build_dir)
    if not os.path.exists(path):
        return False
    with open(path, 'a+') as probe:
        try:
            fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(probe.fileno(), fcntl.LOCK_UN)
        return False


def _run_build(project_root, build_dir):
    """One real `solid build` of the scratch project, as a child process.

    `solid_node.core.loader` appends the cwd to `sys.path` once, in the
    parent; this forked child inherits that entry, so the scratch project
    goes on the path explicitly too.
    """
    os.chdir(project_root)
    sys.path.insert(0, project_root)
    os.environ['SOLID_BUILD_DIR'] = build_dir
    from solid_node.manager.build import Build
    Build().handle(Namespace(path='flat_project/simple_pipe.py'))


class BuildDirectoryAnchorTest(TestCase):
    """A project has one build tree and one build lock. Both are derived from
    the project root, never from the working directory: a command run from a
    subdirectory that published into its own `_build` would take its own lock
    too, so mutual exclusion would hold per-directory instead of per-project
    while the floor watched a tree nothing wrote to."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='solid_node_build_anchor_')
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as stream:
            stream.write('[tool.solid-node]\n'
                         'model = "package.model:Model"\n')
        self.package = os.path.join(self.root, 'package')
        os.mkdir(self.package)
        self.previous = os.getcwd()
        self.addCleanup(os.chdir, self.previous)
        # Another test in this process may have left SOLID_BUILD_DIR set; this
        # one is about the default, so it owns its own environment.
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop('SOLID_BUILD_DIR', None)

    def test_build_dir_and_lock_do_not_move_with_the_working_directory(self):
        os.chdir(self.root)
        from_root = (os.path.realpath(get_build_dir()),
                     os.path.realpath(get_build_lock_path()))

        os.chdir(self.package)
        from_subdirectory = (os.path.realpath(get_build_dir()),
                             os.path.realpath(get_build_lock_path()))

        self.assertEqual(from_root, from_subdirectory)
        self.assertEqual(from_root[0],
                         os.path.realpath(os.path.join(self.root, '_build')))

    def test_an_absolute_build_dir_is_left_alone(self):
        elsewhere = os.path.join(self.root, 'somewhere-else')
        with patch.dict(os.environ, {'SOLID_BUILD_DIR': elsewhere}):
            os.chdir(self.package)
            self.assertEqual(get_build_dir(), elsewhere)


class ProjectBuildLockTest(TestCase):

    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.build_dir = os.path.join(self.root.name, '_build')

    def process(self, target, *args):
        proc = multiprocessing.Process(target=target, args=args)
        self.addCleanup(lambda: proc.is_alive() and proc.kill())
        proc.start()
        return proc

    def test_second_process_waits_until_holder_releases(self):
        ready, release, acquired = (multiprocessing.Event()
                                    for _ in range(3))
        holder = self.process(_hold_lock, self.build_dir, ready, release)
        self.assertTrue(ready.wait(2))
        waiter = self.process(_acquire_lock, self.build_dir, acquired)
        self.assertFalse(acquired.wait(.2))

        release.set()
        self.assertTrue(acquired.wait(2))
        holder.join(2)
        waiter.join(2)
        self.assertEqual(holder.exitcode, 0)
        self.assertEqual(waiter.exitcode, 0)

    def test_killed_holder_releases_lock_for_next_process(self):
        ready, release, acquired = (multiprocessing.Event()
                                    for _ in range(3))
        holder = self.process(_hold_lock, self.build_dir, ready, release)
        self.assertTrue(ready.wait(2))
        os.kill(holder.pid, signal.SIGKILL)
        holder.join(2)

        waiter = self.process(_acquire_lock, self.build_dir, acquired)
        self.assertTrue(acquired.wait(2))
        waiter.join(2)
        self.assertEqual(waiter.exitcode, 0)

    def test_path_follows_published_build_directory(self):
        custom = os.path.join(self.root.name, 'artifacts', 'visible')
        self.assertEqual(get_build_lock_path(custom), f'{custom}.lock')
        self.assertNotEqual(get_build_lock_path(custom),
                            get_build_lock_path(self.build_dir))

    def test_lock_file_is_created_beside_build_directory(self):
        with project_build_lock(self.build_dir):
            self.assertTrue(os.path.isfile(f'{self.build_dir}.lock'))

    def test_lock_file_is_kept_out_of_version_control(self):
        os.makedirs(os.path.join(self.root.name, '.git', 'info'))

        with project_build_lock(self.build_dir):
            pass

        with open(os.path.join(self.root.name,
                               '.git', 'info', 'exclude')) as exclude:
            self.assertIn('_build*', exclude.read().split())

    def test_release_is_not_deferred_by_a_forked_child(self):
        """A child forked while the lock is held inherits the descriptor.

        Releasing explicitly with `LOCK_UN` frees the lock for everyone
        immediately; relying on the descriptor being closed would leave it
        held for as long as any child lives.
        """
        release = multiprocessing.Event()
        with project_build_lock(self.build_dir):
            child = self.process(_idle, release)
            self.assertTrue(lock_is_held(self.build_dir))

        try:
            self.assertFalse(lock_is_held(self.build_dir))
            self.assertTrue(child.is_alive())
        finally:
            release.set()
            child.join(2)


class LockParticipantsTest(TestCase):
    """Every framework producer of artifacts takes the lock -- and gives it
    back as soon as the building stops."""

    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.build_dir = os.path.join(self.root.name, '_build')

    def test_test_runner_releases_the_lock_before_running_tests(self):
        from solid_node.manager.test import Test
        runner = Test()
        node = Mock()
        observed = {}
        node.build_stls.side_effect = lambda: observed.update(
            held=lock_is_held(self.build_dir))

        with patch.dict(os.environ, {'SOLID_BUILD_DIR': self.build_dir}), \
             patch('solid_node.manager.test.load_node', return_value=node), \
             patch.object(runner, 'ensure_node_class'):
            runner.build_node('model.py')

        self.assertTrue(observed['held'],
                        'the node was built without the project build lock')
        self.assertFalse(lock_is_held(self.build_dir),
                         'a test sweep would block the next build')

    def test_export_releases_the_lock_after_building(self):
        from solid_node.core.export import export_node
        node = Mock()
        observed = {}
        node.build_stls.side_effect = lambda: observed.update(
            held=lock_is_held(self.build_dir))

        with patch.dict(os.environ, {'SOLID_BUILD_DIR': self.build_dir}), \
             patch('solid_node.core.export.serialize_node',
                   side_effect=RuntimeError('stop after the build')):
            with self.assertRaises(RuntimeError):
                export_node(node, os.path.join(self.root.name, 'out'),
                            widget=False)

        self.assertTrue(observed['held'])
        self.assertFalse(lock_is_held(self.build_dir))


class PublishedModelFollowsSourceTest(TestCase):
    """The product property, driven through real builds of a real project:
    what a consumer reads is what the source says.

    These render with OpenSCAD, exactly as `solid build` does in a user's
    project, because the defect they guard against -- a build reporting the
    model current and publishing nothing -- was invisible to every test that
    mocked the render.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='solid_node_build_lock_')
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        shutil.copytree(FLAT_PROJECT, os.path.join(self.root, 'flat_project'),
                        ignore=shutil.ignore_patterns('__pycache__'))
        self.source = os.path.join(self.root, 'flat_project', 'simple_pipe.py')
        # A scratch project is a real project: the framework finds its root
        # and its model through the manifest, not through the working
        # directory.
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as stream:
            stream.write('[tool.solid-node]\n'
                         'model = "flat_project.simple_pipe:SimplePipe"\n')

        self.build_dir = os.path.join(self.root, '_build')

    def build(self, count=1):
        procs = [multiprocessing.Process(target=_run_build,
                                         args=(self.root, self.build_dir))
                 for _ in range(count)]
        for proc in procs:
            proc.start()
        for proc in procs:
            proc.join(120)
        for proc in procs:
            self.assertEqual(proc.exitcode, 0)

    def published_stl(self):
        artifacts = glob.glob(os.path.join(self.build_dir, 'flat_project',
                                           'simple_pipe-*.stl'))
        self.assertEqual(len(artifacts), 1, artifacts)
        return artifacts[0]

    def edit(self, radius):
        with open(self.source, 'w') as source:
            source.write('from solid_node.node import Solid2Node\n'
                         'from solid2 import cylinder\n\n\n'
                         'class SimplePipe(Solid2Node):\n\n'
                         '    def render(self):\n'
                         f'        return cylinder(r={radius}, h=100) '
                         '- cylinder(r=8, h=100)\n')

    def test_an_edited_model_reaches_the_published_build(self):
        self.build()
        first = self.published_stl()
        self.assertTrue(os.path.isfile(os.path.join(self.build_dir,
                                                    'viewer.json')))
        with open(first, 'rb') as artifact:
            before = artifact.read()

        self.edit(radius=20)
        self.build()

        published = self.published_stl()
        with open(published, 'rb') as artifact:
            after = artifact.read()
        self.assertNotEqual(before, after,
                            'the edit never reached the published build')
        self.assertEqual(os.path.getmtime(published),
                         os.path.getmtime(self.source),
                         'the published artifact is not the current source')
        # The document is what a consumer reads to find that artifact and to
        # decide whether its geometry moved. A build that renders an artifact
        # exits before writing the document, so the pass that finds the
        # artifact current has to publish it or the model a viewer sees stays
        # a build behind.
        with open(os.path.join(self.build_dir, 'viewer.json')) as document:
            snapshot = json.load(document)
        self.assertEqual(snapshot['root']['mtime'],
                         os.path.getmtime(self.source),
                         'the published document still names the old model')

    def test_concurrent_builds_publish_one_current_model(self):
        self.build(count=3)

        published = self.published_stl()
        self.assertEqual(os.path.getmtime(published),
                         os.path.getmtime(self.source))
        self.assertTrue(os.path.isfile(os.path.join(self.build_dir,
                                                    'viewer.json')))
