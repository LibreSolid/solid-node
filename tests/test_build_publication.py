# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Filesystem-level proofs for direct, per-artifact publication."""

import os
import shutil
import tempfile
import threading
from unittest import TestCase

from solid_node.core.builder import atomic_write, prepare_build_dir


class AtomicArtifactPublicationTest(TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='solid-node-publication-')
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.artifact = os.path.join(self.root, '_build', 'part.stl')
        os.makedirs(os.path.dirname(self.artifact))

    def test_polling_reader_never_observes_a_partial_artifact(self):
        atomic_write(self.artifact, b'old-artifact')
        observed = []
        stop = threading.Event()

        def reader():
            while not stop.is_set():
                with open(self.artifact, 'rb') as artifact:
                    observed.append(artifact.read())

        watcher = threading.Thread(target=reader)
        watcher.start()
        try:
            for _ in range(100):
                atomic_write(self.artifact, b'new-artifact' * 1000)
                atomic_write(self.artifact, b'old-artifact')
        finally:
            stop.set()
            watcher.join()

        self.assertTrue(observed)
        self.assertTrue(all(value in (b'old-artifact',
                                      b'new-artifact' * 1000)
                            for value in observed))

    def test_open_reader_finishes_old_artifact_after_replacement(self):
        atomic_write(self.artifact, b'old-artifact')
        with open(self.artifact, 'rb') as reader:
            atomic_write(self.artifact, b'new-artifact')
            self.assertEqual(reader.read(), b'old-artifact')
        with open(self.artifact, 'rb') as reader:
            self.assertEqual(reader.read(), b'new-artifact')


class PreviousPublicationMigrationTest(TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='solid-node-migration-')
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.build_dir = os.path.join(self.root, '_build')
        self.previous = os.path.join(self.root, '_build.previous')
        self.stale = os.path.join(self.root, '_build.stale')
        os.makedirs(self.previous)
        os.makedirs(self.stale)
        with open(os.path.join(self.previous, 'viewer.json'), 'w') as output:
            output.write('{}')
        os.symlink(os.path.basename(self.previous), self.build_dir)

    def test_symlink_publication_is_converted_once_in_place(self):
        prepare_build_dir(self.build_dir)

        self.assertTrue(os.path.isdir(self.build_dir))
        self.assertFalse(os.path.islink(self.build_dir))
        self.assertTrue(os.path.isfile(os.path.join(self.build_dir,
                                                    'viewer.json')))
        self.assertFalse(os.path.exists(self.stale))


class RenderVisibilityTest(TestCase):
    """A render must not make the previous artifact disappear.

    Rendering used to delete the artifact and point OpenSCAD at its final
    path, so for the whole render — seconds on a real part — a consumer saw
    no file at all, then a growing one. The render now writes a temporary
    sibling that `finish()` moves into place.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='solid-node-render-')
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_render_leaves_the_previous_artifact_in_place(self):
        from unittest.mock import Mock, patch
        from solid_node.node.base import AbstractBaseNode, StlRenderStart

        node = Mock(spec=AbstractBaseNode)
        node.stl_file = os.path.join(self.root, 'part.stl')
        node.scad_file = os.path.join(self.root, 'part.scad')
        node.lock_file = os.path.join(self.root, 'part.stl.lock')
        node.mtime = 0
        node.rigid = True
        node._up_to_date = lambda path: False
        node._stl_generation_locked = False
        node.stl_builder_command_for = \
            AbstractBaseNode.stl_builder_command_for.__get__(node)
        with open(node.stl_file, 'w') as previous:
            previous.write('previous complete artifact')

        with patch('solid_node.node.base.Popen',
                   return_value=Mock(pid=4321)) as popen:
            with self.assertRaises(StlRenderStart) as raised:
                AbstractBaseNode.generate_stl(node)

        with open(node.stl_file) as artifact:
            self.assertEqual(artifact.read(), 'previous complete artifact',
                             'the render removed the artifact readers hold')
        output = popen.call_args[0][0][popen.call_args[0][0].index('-o') + 1]
        self.assertNotEqual(output, node.stl_file,
                            'OpenSCAD wrote straight to the published path')
        self.assertEqual(output, raised.exception.temporary_file)
        self.assertTrue(output.endswith('.tmp'))

        with open(output, 'w') as rendered:
            rendered.write('new artifact')
        raised.exception.finish()

        with open(node.stl_file) as artifact:
            self.assertEqual(artifact.read(), 'new artifact')
        self.assertFalse(os.path.exists(output))
