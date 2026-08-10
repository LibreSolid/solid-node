# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from trimesh.creation import box
from trimesh.util import concatenate

from solid_node.core.builder import (Builder, BuildOutcome, atomic_write,
                                     write_error)
from solid_node.node.base import StlRenderStart

from .test_build_lock import lock_is_held


class BuilderLifecycleTest(TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.builder = Builder('model.py', build_dir=self.root, watch=False)

    def test_render_pass_is_not_a_complete_build(self):
        proc = Mock(pid=123)
        job = StlRenderStart(proc, 'model.stl', 'model.stl.tmp', 0,
                             'model.stl.lock')
        job.wait = Mock()
        self.builder.node = Mock(trigger_stl=Mock(side_effect=job))
        self.assertEqual(asyncio.run(self.builder.generate_stl()),
                         BuildOutcome.RENDERED)
        job.wait.assert_called_once()

    def test_snapshot_is_manifest_last_and_sweeps_old_stls(self):
        old = os.path.join(self.root, 'old.stl')
        current = os.path.join(self.root, 'part.stl')
        open(old, 'w').write('old')
        open(current, 'w').write('current')
        node = SimpleNamespace(rigid=True, name='part', _type='SolidNode',
                               color=None, mtime=0, operations=(),
                               stl_file=current)
        self.builder.node = node
        self.builder._write_viewer_snapshot()
        self.assertTrue(os.path.isfile(os.path.join(self.root, 'viewer.json')))
        self.assertTrue(os.path.isfile(current))
        self.assertFalse(os.path.exists(old))

    def test_successful_snapshot_clears_previous_error(self):
        write_error('previous', self.root)
        current = os.path.join(self.root, 'part.stl')
        open(current, 'w').write('current')
        self.builder.node = SimpleNamespace(
            rigid=True, name='part', _type='SolidNode', color=None, mtime=0,
            operations=(), stl_file=current)
        self.builder._write_viewer_snapshot()
        self.assertFalse(os.path.exists(os.path.join(self.root, 'errors.json')))

    def test_error_file_is_valid_json_while_replaced(self):
        for index in range(20):
            write_error(f'failure {index}', self.root)
            with open(os.path.join(self.root, 'errors.json')) as output:
                self.assertEqual(json.load(output)['error'], f'failure {index}')


class FakeNode:
    """A node stand-in with the real artifact-currency rule.

    A `Mock` cannot be used where currency is under test: `_up_to_date`
    would answer with a truthy Mock and every artifact would look current.
    """

    def __init__(self, stl_file=None, mtime=0, children=(), name='part'):
        self.stl_file = stl_file
        self.rigid = stl_file is not None
        self.mtime = mtime
        self.children = children
        self.files = []
        self.name = name
        self._type = 'SolidNode'
        self.color = None
        self.operations = ()

    def assemble(self):
        pass

    def _up_to_date(self, path):
        return os.path.exists(path) and os.path.getmtime(path) == self.mtime


class PublicationGeometryTest(TestCase):

    def setUp(self):
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def artifact(self, name, mesh, mtime=0):
        path = os.path.join(self.root, name)
        mesh.export(path)
        os.utime(path, (mtime, mtime))
        return path

    def fragmented_mesh(self):
        first = box((2, 2, 2))
        second = box((2, 2, 2))
        second.apply_translation([5, 0, 0])
        return concatenate([first, second])

    def test_fragmented_solid_publishes_on_both_publication_paths(self):
        for already_current in (False, True):
            with self.subTest(already_current=already_current):
                build_dir = os.path.join(
                    self.root, 'current' if already_current else 'rendered')
                os.makedirs(build_dir)
                artifact = os.path.join(build_dir, 'fragmented.stl')
                self.fragmented_mesh().export(artifact)
                os.utime(artifact, (0, 0))
                if already_current:
                    with open(os.path.join(build_dir, 'viewer.json'), 'w') as f:
                        f.write('{"previous": true}')
                node = FakeNode(artifact, mtime=0, name='broken-gear')
                builder = Builder('model.py', build_dir=build_dir, watch=False)

                with patch('solid_node.core.builder.load_node',
                           return_value=node), \
                     patch.object(builder, 'generate_stl',
                                  return_value=BuildOutcome.CURRENT):
                    outcome = asyncio.run(builder._start())

                self.assertEqual(outcome, BuildOutcome.CURRENT)
                self.assertFalse(os.path.exists(
                    os.path.join(build_dir, 'errors.json')))
                with open(os.path.join(build_dir, 'viewer.json')) as f:
                    self.assertEqual(json.load(f)['root']['name'],
                                     'broken-gear')


class BuildOutcomeTest(TestCase):
    """The process supervisor needs lifecycle meanings, not just exit 0."""

    def setUp(self):
        self.builder = Builder('model.py')
        self.builder.node = Mock(rigid=False, children=())

    def test_current_model_is_a_complete_build(self):
        self.assertEqual(asyncio.run(self.builder.generate_stl()),
                         BuildOutcome.CURRENT)

    def test_a_locked_but_missing_artifact_is_not_current(self):
        node = FakeNode(stl_file='still-rendering.stl')
        node.trigger_stl = Mock()
        self.builder.node = node

        self.assertEqual(asyncio.run(self.builder.generate_stl()),
                         BuildOutcome.RENDERED)

    def test_source_change_has_its_own_outcome(self):
        async def wait_for_source_change():
            waiting = asyncio.create_task(self.builder.wait_for_change())
            await asyncio.sleep(0)
            self.builder.file_changed.set_result(True)
            return await waiting

        self.assertEqual(asyncio.run(wait_for_source_change()),
                         BuildOutcome.SOURCE_CHANGED)


class RedundantAndSupersededBuildTest(TestCase):
    """A builder re-evaluates its work after taking the project build lock.

    Artifacts now live where consumers read them, so currency is judged in
    the build directory itself; what has to be guarded is that a redundant
    build renders nothing, that finding the model current does not end a
    watch, and that a build which waited while a newer edit landed stands
    down instead of publishing what it loaded first.
    """

    def setUp(self):
        # `_start()` exports SOLID_BUILD_DIR for the render subprocess; without
        # this the export outlives the test and every later test in the process
        # builds into a directory that no longer exists.
        environment = patch.dict(os.environ, {'SOLID_BUILD_DIR': '_build'})
        environment.start()
        self.addCleanup(environment.stop)

    def build_fixture(self, artifact_current):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        build_dir = os.path.join(root, '_build')
        os.makedirs(build_dir)
        with open(os.path.join(build_dir, 'viewer.json'), 'w') as snapshot:
            snapshot.write('{}')

        artifact = os.path.join(build_dir, 'part.stl')
        if artifact_current:
            box((2, 2, 2)).export(artifact)
            os.utime(artifact, (0, 0))

        node = FakeNode(stl_file=artifact, mtime=0)
        return Builder('model.py', build_dir=build_dir, watch=False), node

    def publish_matching_document(self, builder, node):
        """Leave the build directory in the state a finished build leaves."""
        builder.node = node
        self.assertTrue(builder._write_viewer_snapshot())
        builder.node = None
        return os.path.join(builder.build_dir, 'viewer.json')

    def test_current_model_is_not_built_again(self):
        builder, node = self.build_fixture(artifact_current=True)
        document = self.publish_matching_document(builder, node)
        before = os.stat(document).st_mtime_ns

        with patch('solid_node.core.builder.load_node', return_value=node), \
             patch.object(builder, 'generate_stl') as generate, \
             patch.object(builder, '_notify_callback') as callback:
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.CURRENT)
        generate.assert_not_called()
        self.assertEqual(os.stat(document).st_mtime_ns, before,
                         'a redundant build rewrote the document')
        callback.assert_not_called()

    def test_a_current_artifact_still_republishes_a_stale_document(self):
        """The pass that renders an artifact exits before writing the
        document; the pass that finds the artifact current must publish it,
        or a consumer reads the previous model's manifest forever."""
        builder, node = self.build_fixture(artifact_current=True)
        document = os.path.join(builder.build_dir, 'viewer.json')

        with patch('solid_node.core.builder.load_node', return_value=node), \
             patch.object(builder, 'generate_stl') as generate, \
             patch.object(builder, '_notify_callback') as callback:
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.CURRENT)
        generate.assert_not_called()
        with open(document) as published:
            snapshot = json.load(published)
        self.assertEqual(snapshot['root']['name'], 'part')
        self.assertEqual(snapshot['root']['mtime'], node.mtime)
        callback.assert_called_once()

    def test_a_watching_builder_waits_after_finding_the_model_current(self):
        """Skipping redundant work does not end a watch.

        A watching builder that exits the moment it finds the model current
        is respawned immediately by the develop loop, which then spins on
        that builder forever instead of waiting for the next edit.
        """
        builder, node = self.build_fixture(artifact_current=True)
        builder.watch = True
        self.addCleanup(builder.observer.stop)

        async def scenario():
            building = asyncio.ensure_future(builder._start())
            for _ in range(200):
                await asyncio.sleep(0.01)
                if builder.file_changed is not None:
                    break
            self.assertIsNotNone(builder.file_changed,
                                 'the builder exited instead of waiting')
            self.assertFalse(lock_is_held(builder.build_dir),
                             'waiting for an edit held the build lock')
            builder.file_changed.set_result(True)
            return await building

        with patch('solid_node.core.builder.load_node', return_value=node), \
             patch.object(builder, 'generate_stl') as generate:
            outcome = asyncio.run(scenario())

        self.assertEqual(outcome, BuildOutcome.SOURCE_CHANGED)
        generate.assert_not_called()

    def test_source_moving_under_a_waiting_build_stands_it_down(self):
        """The newest source wins: a build that waited for the lock while a
        newer edit was built must not publish what it loaded first."""
        builder, node = self.build_fixture(artifact_current=False)

        @contextmanager
        def lock_taken_late(build_dir=None):
            node.mtime += 1          # an edit landed while this build waited
            yield

        with patch('solid_node.core.builder.load_node', return_value=node), \
             patch('solid_node.core.builder.project_build_lock',
                   lock_taken_late), \
             patch.object(builder, 'generate_stl') as generate, \
             patch.object(builder, '_write_viewer_snapshot') as snapshot:
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.SOURCE_CHANGED)
        generate.assert_not_called()
        snapshot.assert_not_called()


class BuildCallbackTest(TestCase):

    def setUp(self):
        # `_start()` exports SOLID_BUILD_DIR for the render subprocess; without
        # this the export outlives the test and every later test in the process
        # builds into a directory that no longer exists.
        environment = patch.dict(os.environ, {'SOLID_BUILD_DIR': '_build'})
        environment.start()
        self.addCleanup(environment.stop)
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_callback_posts_exact_url_without_body(self):
        builder = Builder('model.py', build_dir=self.root, watch=False,
                          callback='http://listener/build-ready?token=opaque')
        response = Mock()
        with patch('httpx.post', return_value=response) as post:
            builder._notify_callback()

        post.assert_called_once_with(
            'http://listener/build-ready?token=opaque', content=b'', timeout=2.0)
        response.raise_for_status.assert_called_once()

    def test_callback_failure_is_best_effort(self):
        builder = Builder('model.py', build_dir=self.root, watch=False,
                          callback='http://listener/build-ready')
        with patch('httpx.post', side_effect=OSError('not listening')):
            builder._notify_callback()

    def test_complete_build_publishes_before_callback(self):
        builder = Builder('model.py', build_dir=self.root, watch=False,
                          callback='http://listener/build-ready')
        events = []

        with patch('solid_node.core.builder.load_node',
                   return_value=Mock(children=())), \
             patch.object(builder, 'generate_stl',
                          return_value=BuildOutcome.CURRENT), \
             patch.object(builder, '_write_viewer_snapshot',
                          side_effect=lambda: events.append('snapshot')), \
             patch.object(builder, '_notify_callback',
                          side_effect=lambda: events.append('callback')):
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.CURRENT)
        self.assertEqual(events, ['snapshot', 'callback'])

    def test_callback_is_notified_outside_the_build_lock(self):
        """Notifying a consumer is not build work; a callback that blocks
        must not hold the next builder off."""
        builder = Builder('model.py', build_dir=self.root, watch=False,
                          callback='http://listener/build-ready')
        held = []

        @contextmanager
        def recording_lock(build_dir=None):
            held.append('acquired')
            try:
                yield
            finally:
                held.append('released')

        with patch('solid_node.core.builder.load_node',
                   return_value=Mock(children=())), \
             patch('solid_node.core.builder.project_build_lock',
                   recording_lock), \
             patch.object(builder, 'generate_stl',
                          return_value=BuildOutcome.CURRENT), \
             patch.object(builder, '_write_viewer_snapshot'), \
             patch.object(builder, '_notify_callback',
                          side_effect=lambda: held.append('callback')):
            asyncio.run(builder._start())

        self.assertEqual(held, ['acquired', 'released', 'callback'])

    def test_failed_build_does_not_notify_callback(self):
        builder = Builder('model.py', build_dir=self.root, watch=False,
                          callback='http://listener/build-ready')
        with patch('solid_node.core.builder.load_node',
                   side_effect=RuntimeError('broken model')), \
             patch.object(builder, '_notify_callback') as callback:
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.FAILED)
        callback.assert_not_called()


class ViewerSnapshotContentTest(TestCase):
    """The snapshot is the document the viewer reads; its shape is a
    contract, not an implementation detail."""

    def test_snapshot_names_one_artifact_and_carries_its_mtime(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        builder = Builder('model.py', build_dir=root, watch=False)
        artifact = os.path.join(root, 'part.stl')
        with open(artifact, 'w') as handle:
            handle.write('solid part')
        builder.node = SimpleNamespace(
            name='part', rigid=True, _type='SolidNode', color=None, mtime=0,
            operations=(), stl_file=artifact)

        builder._write_viewer_snapshot()

        with open(os.path.join(root, 'viewer.json')) as snapshot:
            data = json.load(snapshot)
        self.assertEqual(data['format'], 'solid-node-export')
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['root']['name'], 'part')
        self.assertEqual(data['root']['model'], 'part.stl')
        self.assertEqual(data['root']['mtime'], 0)
        self.assertEqual(
            set(data['root']),
            {'name', 'type', 'color', 'mtime', 'operations', 'model'},
        )
        self.assertEqual(data['animation'], {'fps': 30, 'frames': 360})
        self.assertEqual(sorted(os.listdir(root)), ['part.stl', 'viewer.json'])


class PublicationOrderingTest(TestCase):
    """The manifest is what makes an artifact reachable, so it is written
    last and nothing it still names is ever swept."""

    def setUp(self):
        # `_start()` exports SOLID_BUILD_DIR for the render subprocess; without
        # this the export outlives the test and every later test in the process
        # builds into a directory that no longer exists.
        environment = patch.dict(os.environ, {'SOLID_BUILD_DIR': '_build'})
        environment.start()
        self.addCleanup(environment.stop)
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.builder = Builder('model.py', build_dir=self.root, watch=False)

    def node_for(self, *names):
        def leaf(name):
            path = os.path.join(self.root, f'{name}.stl')
            with open(path, 'w') as artifact:
                artifact.write(name)
            return SimpleNamespace(name=name, rigid=True, _type='SolidNode',
                                   color=None, mtime=0, operations=(),
                                   stl_file=path)
        children = [leaf(name) for name in names]
        return SimpleNamespace(name='assembly', rigid=False, _type='Assembly',
                               color=None, mtime=0, operations=(),
                               children=children,
                               render=lambda: children,
                               _link_child=lambda child: None)

    def test_an_added_artifact_is_readable_before_the_manifest_names_it(self):
        observed = []
        self.builder.node = self.node_for('part', 'added')
        real_write = atomic_write

        def watching_write(path, content):
            if os.path.basename(path) == 'viewer.json':
                observed.append(os.path.exists(
                    os.path.join(self.root, 'added.stl')))
            real_write(path, content)

        with patch('solid_node.core.builder.atomic_write', watching_write):
            self.builder._write_viewer_snapshot()

        self.assertEqual(observed, [True],
                         'the manifest named an artifact that was not there')

    def test_a_dropped_artifact_outlives_the_manifest_that_named_it(self):
        self.builder.node = self.node_for('part', 'dropped')
        self.builder._write_viewer_snapshot()
        self.assertTrue(os.path.exists(os.path.join(self.root, 'dropped.stl')))

        observed = []
        real_write = atomic_write

        def watching_write(path, content):
            real_write(path, content)
            if os.path.basename(path) == 'viewer.json':
                observed.append(os.path.exists(
                    os.path.join(self.root, 'dropped.stl')))

        self.builder.node = self.node_for('part')
        with patch('solid_node.core.builder.atomic_write', watching_write):
            self.builder._write_viewer_snapshot()

        self.assertEqual(observed, [True],
                         'the artifact went before the manifest dropping it')
        self.assertFalse(os.path.exists(os.path.join(self.root, 'dropped.stl')))

    def test_a_renamed_node_leaves_no_artifact_behind(self):
        self.builder.node = self.node_for('part', 'old_name')
        self.builder._write_viewer_snapshot()

        self.builder.node = self.node_for('part', 'new_name')
        self.builder._write_viewer_snapshot()

        self.assertEqual(sorted(os.listdir(self.root)),
                         ['new_name.stl', 'part.stl', 'viewer.json'])

    def test_the_sweep_spares_inputs_locks_and_in_flight_temporaries(self):
        self.builder.node = self.node_for('part')
        for spared in ('part.scad', 'part.stl.lock', '.part.stl.abc123.tmp'):
            with open(os.path.join(self.root, spared), 'w') as handle:
                handle.write('keep me')
        write_error('previous failure', self.root)

        self.builder._write_viewer_snapshot()

        remaining = set(os.listdir(self.root))
        self.assertLessEqual({'part.scad', 'part.stl.lock',
                              '.part.stl.abc123.tmp'}, remaining)

    def test_a_failed_build_sweeps_nothing(self):
        """The sweep is driven by a manifest, and a failed build writes no
        manifest, so nothing a previous build published is removed."""
        self.builder.node = self.node_for('part', 'other')
        self.builder._write_viewer_snapshot()
        before = sorted(os.listdir(self.root))

        with patch('solid_node.core.builder.load_node',
                   side_effect=RuntimeError('broken model')):
            outcome = asyncio.run(self.builder._start())

        self.assertEqual(outcome, BuildOutcome.FAILED)
        self.assertLessEqual(set(before), set(os.listdir(self.root)))
