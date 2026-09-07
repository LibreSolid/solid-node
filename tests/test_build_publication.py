# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Filesystem-level proofs for direct, per-artifact publication."""

import os
import shutil
import tempfile
import threading
from subprocess import CalledProcessError
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
        self.notes = os.path.join(self.root, '_build.notes')
        self.lock = os.path.join(self.root, '_build.lock')
        os.makedirs(self.previous)
        os.makedirs(self.stale)
        with open(os.path.join(self.previous, 'viewer.json'), 'w') as output:
            output.write('{}')
        with open(os.path.join(self.stale, 'keep.txt'), 'w') as output:
            output.write('unowned sibling')
        with open(self.notes, 'w') as output:
            output.write('user notes')
        with open(self.lock, 'w') as output:
            output.write('held elsewhere')
        os.symlink(os.path.basename(self.previous), self.build_dir)

    def test_symlink_publication_is_converted_once_in_place(self):
        prepare_build_dir(self.build_dir)

        self.assertTrue(os.path.isdir(self.build_dir))
        self.assertFalse(os.path.islink(self.build_dir))
        self.assertTrue(os.path.isfile(os.path.join(self.build_dir,
                                                    'viewer.json')))
        self.assertFalse(os.path.exists(self.previous))
        self.assertTrue(os.path.isfile(os.path.join(self.stale, 'keep.txt')))
        self.assertTrue(os.path.isfile(self.notes))
        self.assertTrue(os.path.isfile(self.lock))


class BuildDirectoryPreparationOwnershipTest(TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='solid-node-preparation-')
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.build_dir = os.path.join(self.root, '_build')
        os.makedirs(self.build_dir)

    def test_ordinary_preparation_preserves_every_sibling(self):
        notes = os.path.join(self.root, '_build.notes')
        backup = os.path.join(self.root, '_build.backup')
        legacy_looking = os.path.join(self.root, '_build.a1b2c3d4')
        with open(notes, 'w') as output:
            output.write('user notes')
        os.makedirs(backup)
        with open(os.path.join(backup, 'keep.txt'), 'w') as output:
            output.write('user backup')
        os.makedirs(legacy_looking)
        with open(os.path.join(legacy_looking, 'viewer.json'), 'w') as output:
            output.write('user-controlled data')

        prepare_build_dir(self.build_dir)

        self.assertTrue(os.path.isfile(notes))
        self.assertTrue(os.path.isfile(os.path.join(backup, 'keep.txt')))
        self.assertTrue(os.path.isfile(os.path.join(
            legacy_looking, 'viewer.json')))


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
        node.mtime_ns = 0
        # Stubbed for the same reason mtime_ns is: both are read straight
        # out of the node and written to the filesystem, and a Mock's
        # stand-in for either is not something a file can hold. None is
        # the honest value here -- nothing vouches for this artifact.
        node.source_digest = None
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

    def test_failed_render_discards_private_files_and_preserves_artifact(self):
        from unittest.mock import Mock
        from solid_node.node.base import StlRenderStart

        target = os.path.join(self.root, 'part.stl')
        temporary = os.path.join(self.root, '.part.stl.failed.tmp')
        lock = os.path.join(self.root, 'part.stl.lock')
        with open(target, 'w') as artifact:
            artifact.write('previous complete artifact')
        with open(temporary, 'w') as artifact:
            artifact.write('failed renderer output')
        with open(lock, 'w') as handle:
            handle.write('4321')

        proc = Mock(args=['openscad', 'part.scad'], pid=4321)
        proc.wait.return_value = 1
        job = StlRenderStart(proc, target, temporary, 0, lock)

        with self.assertRaises(CalledProcessError) as raised:
            job.wait()

        self.assertEqual(raised.exception.returncode, 1)
        with open(target) as artifact:
            self.assertEqual(artifact.read(), 'previous complete artifact')
        self.assertFalse(os.path.exists(temporary))
        self.assertFalse(os.path.exists(lock))
