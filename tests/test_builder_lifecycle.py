# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import Mock, patch

from solid_node.core.builder import Builder, BuildOutcome, BuildSession
from solid_node.node.base import StlRenderStart

from .test_build_lock import lock_is_held


class FakeNode:
    """A node stand-in with the real artifact-currency rule.

    A `Mock` cannot be used where currency is under test: `_up_to_date`
    would answer with a truthy Mock and every artifact would look current.
    """

    def __init__(self, stl_file=None, mtime=0, children=()):
        self.stl_file = stl_file
        self.rigid = stl_file is not None
        self.mtime = mtime
        self.children = children
        self.files = []

    def assemble(self):
        pass

    def _up_to_date(self, path):
        return os.path.exists(path) and os.path.getmtime(path) == self.mtime


class BuilderLifecycleTest(TestCase):
    """The process supervisor needs lifecycle meanings, not just exit 0."""

    def setUp(self):
        self.builder = Builder('model.py')
        self.builder.node = Mock()

    def test_render_pass_is_not_a_complete_build(self):
        proc = Mock()
        proc.pid = 123
        job = StlRenderStart(proc, 'model.stl', 0, 'model.stl.lock')
        job.wait = Mock()
        self.builder.node.trigger_stl.side_effect = job

        outcome = asyncio.run(self.builder.generate_stl())

        self.assertEqual(outcome, BuildOutcome.RENDERED)
        job.wait.assert_called_once()

    def test_current_model_is_a_complete_build(self):
        outcome = asyncio.run(self.builder.generate_stl())

        self.assertEqual(outcome, BuildOutcome.CURRENT)

    def test_source_change_has_its_own_outcome(self):
        async def wait_for_source_change():
            waiting = asyncio.create_task(self.builder.wait_for_change())
            await asyncio.sleep(0)
            self.builder.file_changed.set_result(True)
            return await waiting

        outcome = asyncio.run(wait_for_source_change())

        self.assertEqual(outcome, BuildOutcome.SOURCE_CHANGED)

    def test_discarding_failed_candidate_keeps_previous_build(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        build_dir = os.path.join(root, '_build')
        os.mkdir(build_dir)
        with open(os.path.join(build_dir, 'model.stl'), 'w') as artifact:
            artifact.write('previous complete model')
        with open(os.path.join(build_dir, 'viewer.json'), 'w') as snapshot:
            snapshot.write('{"version": 1, "root": {"name": "model"}}')

        session = BuildSession(build_dir)
        with open(os.path.join(session.staging_dir, 'model.stl'), 'w') as artifact:
            artifact.write('partial replacement')
        session.discard()

        with open(os.path.join(build_dir, 'model.stl')) as artifact:
            self.assertEqual(artifact.read(), 'previous complete model')
        with open(os.path.join(build_dir, 'viewer.json')) as snapshot:
            self.assertIn('"name": "model"', snapshot.read())

    def test_callback_posts_exact_url_without_body(self):
        self.builder.callback = 'http://listener/build-ready?token=opaque'
        response = Mock()
        with patch('httpx.post', return_value=response) as post:
            self.builder._notify_callback()

        post.assert_called_once_with(
            'http://listener/build-ready?token=opaque', content=b'', timeout=2.0)
        response.raise_for_status.assert_called_once()

    def test_callback_failure_is_best_effort(self):
        self.builder.callback = 'http://listener/build-ready'
        with patch('httpx.post', side_effect=OSError('not listening')):
            self.builder._notify_callback()

    def test_complete_build_publishes_before_callback(self):
        builder = Builder('model.py', build_dir='/tmp/candidate',
                          published_build_dir='/tmp/published', watch=False,
                          callback='http://listener/build-ready')
        node = Mock()
        events = []
        with patch.dict(os.environ, {'SOLID_BUILD_DIR': '_build'}), \
             patch('solid_node.core.builder.load_node', return_value=node), \
             patch.object(builder, 'generate_stl',
                          return_value=BuildOutcome.CURRENT), \
             patch.object(builder, '_write_viewer_snapshot'), \
             patch.object(builder, '_publish', side_effect=lambda: events.append('publish')), \
             patch.object(builder, '_notify_callback',
                          side_effect=lambda: events.append('callback')):
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.CURRENT)
        self.assertEqual(events, ['publish', 'callback'])

    def dedup_fixture(self, artifact_in):
        """A one-artifact model whose STL is current in `artifact_in`.

        The candidate and the published directory are distinct, as they are
        in every real build, so where the artifact sits decides whether the
        publication already covers this source state.
        """
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        candidate = os.path.join(root, 'candidate')
        published = os.path.join(root, 'published')
        os.makedirs(candidate)
        os.makedirs(published)
        with open(os.path.join(published, 'viewer.json'), 'w') as snapshot:
            snapshot.write('{}')

        artifact = os.path.join(
            {'candidate': candidate, 'published': published}[artifact_in],
            'part.stl')
        with open(artifact, 'w') as handle:
            handle.write('solid part')
        os.utime(artifact, (0, 0))

        node = FakeNode(stl_file=os.path.join(candidate, 'part.stl'), mtime=0)
        return Builder('model.py', build_dir=candidate,
                       published_build_dir=published, watch=False), node

    def test_current_published_model_is_not_published_again(self):
        builder, node = self.dedup_fixture(artifact_in='published')

        with patch.dict(os.environ, {'SOLID_BUILD_DIR': '_build'}), \
             patch('solid_node.core.builder.load_node', return_value=node), \
             patch.object(builder, 'generate_stl') as generate, \
             patch.object(builder, '_publish') as publish:
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.CURRENT)
        generate.assert_not_called()
        publish.assert_not_called()

    def test_candidate_artifacts_do_not_count_as_published(self):
        """A rendered artifact nobody can read yet is not a publication.

        A build that needs more than one render pass leaves its artifacts in
        the candidate directory and exits; the next pass must still publish
        them. Reading currency from the candidate made every multi-pass build
        report the model current and publish nothing, so an edited model
        never reached a consumer.
        """
        builder, node = self.dedup_fixture(artifact_in='candidate')

        with patch.dict(os.environ, {'SOLID_BUILD_DIR': '_build'}), \
             patch('solid_node.core.builder.load_node', return_value=node), \
             patch.object(builder, 'generate_stl',
                          return_value=BuildOutcome.CURRENT), \
             patch.object(builder, '_write_viewer_snapshot'), \
             patch.object(builder, '_publish') as publish:
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.CURRENT)
        publish.assert_called_once()

    def test_a_watching_builder_waits_after_finding_the_model_current(self):
        """Skipping redundant work does not end a watch.

        A watching builder that exits the moment it finds the model current
        is respawned immediately by the develop loop, which then spins on
        that builder forever instead of waiting for the next edit.
        """
        builder, node = self.dedup_fixture(artifact_in='published')
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
            self.assertFalse(lock_is_held(builder.published_build_dir),
                             'waiting for an edit held the build lock')
            builder.file_changed.set_result(True)
            return await building

        with patch.dict(os.environ, {'SOLID_BUILD_DIR': '_build'}), \
             patch('solid_node.core.builder.load_node', return_value=node), \
             patch.object(builder, 'generate_stl') as generate, \
             patch.object(builder, '_publish') as publish:
            outcome = asyncio.run(scenario())

        self.assertEqual(outcome, BuildOutcome.SOURCE_CHANGED)
        generate.assert_not_called()
        publish.assert_not_called()

    def test_source_moving_under_a_waiting_build_stands_it_down(self):
        """The newest source wins: a build that waited for the lock while a
        newer edit was built must not publish what it loaded first."""
        builder, node = self.dedup_fixture(artifact_in='candidate')

        @contextmanager
        def lock_taken_late(build_dir=None):
            node.mtime += 1          # an edit landed while this build waited
            yield

        with patch.dict(os.environ, {'SOLID_BUILD_DIR': '_build'}), \
             patch('solid_node.core.builder.load_node', return_value=node), \
             patch('solid_node.core.builder.project_build_lock',
                   lock_taken_late), \
             patch.object(builder, 'generate_stl') as generate, \
             patch.object(builder, '_publish') as publish:
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.SOURCE_CHANGED)
        generate.assert_not_called()
        publish.assert_not_called()

    def test_callback_is_notified_outside_the_build_lock(self):
        """Notifying a consumer is not build work; a callback that blocks
        must not hold the next builder off."""
        builder, node = self.dedup_fixture(artifact_in='candidate')
        builder.callback = 'http://listener/build-ready'
        held = []

        @contextmanager
        def recording_lock(build_dir=None):
            held.append('acquired')
            try:
                yield
            finally:
                held.append('released')

        with patch.dict(os.environ, {'SOLID_BUILD_DIR': '_build'}), \
             patch('solid_node.core.builder.load_node', return_value=node), \
             patch('solid_node.core.builder.project_build_lock',
                   recording_lock), \
             patch.object(builder, 'generate_stl',
                          return_value=BuildOutcome.CURRENT), \
             patch.object(builder, '_write_viewer_snapshot'), \
             patch.object(builder, '_publish'), \
             patch.object(builder, '_notify_callback',
                          side_effect=lambda: held.append('callback')):
            asyncio.run(builder._start())

        self.assertEqual(held, ['acquired', 'released', 'callback'])

    def test_complete_build_writes_viewer_snapshot_before_publishing(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        builder = Builder('model.py', build_dir=root, published_build_dir=root,
                          watch=False)
        rigid = Mock(name='part', rigid=True, operations=(), stl_file=os.path.join(root, 'part.stl'))
        rigid.name = 'part'
        rigid.rigid = True
        rigid.operations = ()
        rigid._type = 'SolidNode'
        rigid.color = None
        rigid.mtime = 0
        with open(rigid.stl_file, 'w') as artifact:
            artifact.write('solid part')
        builder.node = rigid

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
        self.assertFalse(os.path.isdir(os.path.join(root, 'models')))
        self.assertEqual(sorted(os.listdir(root)), ['part.stl', 'viewer.json'])

    def test_failed_build_does_not_notify_callback(self):
        builder = Builder('model.py', build_dir='/tmp/candidate',
                          published_build_dir='/tmp/published', watch=False,
                          callback='http://listener/build-ready')
        with patch.dict(os.environ, {'SOLID_BUILD_DIR': '_build'}), \
             patch('solid_node.core.builder.load_node',
                   side_effect=RuntimeError('broken model')), \
             patch.object(builder, '_notify_callback') as callback:
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.FAILED)
        callback.assert_not_called()


class LostPublicationRaceTest(TestCase):
    """Another publisher winning the race is not a broken model: it left
    its own complete artifact set behind, which every reader can use. A
    build that produced a correct model must not fail with a traceback
    because it lost that race."""

    def test_publication_failure_is_reported_not_raised(self):
        published = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, published, ignore_errors=True)
        builder = Builder('model.py', build_dir='/tmp/candidate',
                          published_build_dir=published, watch=False,
                          callback='http://listener/build-ready')
        notified = []

        with patch.dict(os.environ, {'SOLID_BUILD_DIR': '_build'}), \
             patch('solid_node.core.builder.load_node', return_value=Mock()), \
             patch.object(builder, 'generate_stl',
                          return_value=BuildOutcome.CURRENT), \
             patch.object(builder, '_write_viewer_snapshot'), \
             patch.object(builder, '_publish',
                          side_effect=OSError('another publisher won')), \
             patch.object(builder, '_notify_callback',
                          side_effect=lambda: notified.append('callback')):
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.FAILED)
        self.assertEqual(notified, [])
        with open(os.path.join(published, 'errors.json')) as report:
            self.assertIn('another publisher won', json.load(report)['error'])
