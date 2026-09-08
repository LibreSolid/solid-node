# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""`trimesh` belongs to the path that reads meshes, not to every path
that touches a node module.

`solid_node/node/base.py` used to import `trimesh` at module scope for a
single call site inside `cached_base_mesh`, so every command that reached
any node module paid 0.64 s for a mesh library it might never ask a
question of. These tests pin the deferral from both sides: importing the
node base must not reach for the library, and the one path that does need
it must still behave exactly as ADR-028 says it does.

The behavioural half matters as much as the import half. Moving an import
is only safe if nothing about the cache moved with it, so the same
strong-observation keying, the same stale-entry eviction and the same
shared cached object are asserted here beside the import assertions --
a green import test over a quietly broken cache would be worse than no
change at all.
"""

import os
import tempfile
from unittest import TestCase

import trimesh
from trimesh.creation import box

from solid_node.node import base
from solid_node.node.base import cached_base_mesh
from solid_node._artifact import artifact_cache_key

from .import_probe import probe, probe_import


class MeshLibraryImportTest(TestCase):
    """What importing the node base costs, observed in a process that
    has not already imported it -- the only place the answer is honest,
    since the test runner has loaded the whole framework by now."""

    def test_importing_node_base_does_not_import_trimesh(self):
        result = probe_import('solid_node.node.base')

        self.assertEqual(result.status, 0, result.stderr)
        self.assertFalse(
            result.imported('trimesh'),
            'importing solid_node.node.base reached for trimesh; the mesh '
            'library must be imported by the path that reads meshes')

    def test_reading_a_mesh_imports_trimesh_and_returns_it(self):
        """The deferral must not have turned into an omission: the path
        that loads an STL still loads it, through the real library."""
        with tempfile.TemporaryDirectory(prefix='solid-mesh-defer-') as scratch:
            stl_file = os.path.join(scratch, 'part.stl')
            box((2, 3, 4)).export(stl_file)

            result = probe(
                'from solid_node.node.base import cached_base_mesh\n'
                f'mesh = cached_base_mesh({stl_file!r})\n'
                'print("VOLUME", round(mesh.volume, 6))\n')

        self.assertEqual(result.status, 0, result.stderr)
        self.assertIn('VOLUME 24.0', result.stdout)
        self.assertTrue(
            result.imported('trimesh'),
            'reading an STL must import trimesh, not silently do without it')


class CachedBaseMeshUnchangedTest(TestCase):
    """ADR-028's cache, unchanged by the deferral: one load per strong
    artifact observation, the cached object itself handed back, and any entry
    under the file's old identity evicted on the next access."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.stl_path = os.path.join(self.tmpdir.name, 'part.stl')
        box((2, 3, 4)).export(self.stl_path)

        # The cache is module state shared with every other test in the
        # run, so this test owns its own entries and puts back whatever
        # it found -- otherwise an eviction assertion here would depend
        # on what ran before it.
        preexisting = dict(base._base_mesh_cache)
        base._base_mesh_cache.clear()
        self.addCleanup(base._base_mesh_cache.update, preexisting)
        self.addCleanup(base._base_mesh_cache.clear)

    def test_two_reads_of_an_unchanged_file_share_one_mesh(self):
        first = cached_base_mesh(self.stl_path)
        second = cached_base_mesh(self.stl_path)

        self.assertIs(first, second)
        self.assertIsInstance(first, trimesh.Trimesh)
        self.assertEqual(
            list(base._base_mesh_cache),
            [artifact_cache_key(self.stl_path)])

    def test_a_changed_mtime_evicts_the_stale_entry(self):
        stale = cached_base_mesh(self.stl_path)
        old_mtime = os.path.getmtime(self.stl_path)
        old_key = artifact_cache_key(self.stl_path)

        box((6, 6, 6)).export(self.stl_path)
        newer = old_mtime + 5
        os.utime(self.stl_path, (newer, newer))

        fresh = cached_base_mesh(self.stl_path)

        self.assertIsNot(fresh, stale)
        self.assertAlmostEqual(fresh.volume, 216.0, places=4)
        # A rebuild loop must not accumulate one cached mesh per
        # rebuild: the entry under the old mtime is gone, not merely
        # shadowed by a newer one.
        self.assertNotIn(old_key, base._base_mesh_cache)
        self.assertEqual(list(base._base_mesh_cache),
                         [artifact_cache_key(self.stl_path)])
