# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import asyncio
import os
import shutil
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch

from solid_node.core.builder import Builder, BuildOutcome, BuildSession
from solid_node.node.base import StlRenderStart


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

        session = BuildSession(build_dir)
        with open(os.path.join(session.staging_dir, 'model.stl'), 'w') as artifact:
            artifact.write('partial replacement')
        session.discard()

        with open(os.path.join(build_dir, 'model.stl')) as artifact:
            self.assertEqual(artifact.read(), 'previous complete model')

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
             patch.object(builder, '_publish', side_effect=lambda: events.append('publish')), \
             patch.object(builder, '_notify_callback',
                          side_effect=lambda: events.append('callback')):
            outcome = asyncio.run(builder._start())

        self.assertEqual(outcome, BuildOutcome.CURRENT)
        self.assertEqual(events, ['publish', 'callback'])

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
