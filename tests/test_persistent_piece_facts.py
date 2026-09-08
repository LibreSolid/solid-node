# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""WP3: persistent facts remain useful only behind one verified STL."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import trimesh

from solid_node._artifact import ArtifactChanged, ArtifactSnapshot
from solid_node.core import pieces
from solid_node.core.builder import Builder, write_error
from solid_node.core.export import export_node
from solid_node.node import base
from solid_node import test as test_module
from tests.test_export import Cube


def box_bytes(extents):
    return trimesh.creation.box(extents).export(file_type='stl')


class CurrentNode:
    def __init__(self, path, source=__file__):
        self.stl_file = str(path)
        self.src = source

    def _up_to_date(self, path):
        return True


class RenamedNode(CurrentNode):
    pass


class GeometryNode:
    exact = False
    flexible = False
    rigid = True

    def __init__(self, name, path, offset=(0, 0, 0)):
        self.name = name
        self.stl_file = str(path)
        self.matrix = np.eye(4)
        self.matrix[:3, 3] = offset


class GeometryAssembly:
    rigid = False

    def __init__(self, children):
        self.children = children


class PersistentPieceFactsTest(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix='solid-piece-facts-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.artifact = self.root / 'part.stl'
        self.first = box_bytes((1, 2, 3))
        self.second = box_bytes((4, 5, 6))
        self.assertEqual(len(self.first), len(self.second))
        self.artifact.write_bytes(self.first)
        self.node = CurrentNode(self.artifact)

    def register(self, node=None, model='part.stl', **kwargs):
        with pieces.PieceInventory(**kwargs) as inventory:
            identity = inventory.register(node or self.node, model)
            result = inventory.pieces()
        return identity, result

    def test_a_second_publication_reuses_only_artifact_facts(self):
        real_geometry = pieces._geometry_facts_from_bytes
        real_digest = pieces._digest_bytes
        geometry_calls = []
        digest_calls = []

        def geometry(path, data):
            geometry_calls.append(path)
            return real_geometry(path, data)

        def digest(data):
            digest_calls.append(len(data))
            return real_digest(data)

        with (patch.object(pieces, '_geometry_facts_from_bytes', geometry),
              patch.object(pieces, '_digest_bytes', digest)):
            first_id, first = self.register()
            second_id, second = self.register(
                RenamedNode(self.artifact), model='renamed/part.stl')

        self.assertEqual(geometry_calls, [str(self.artifact)])
        self.assertEqual(digest_calls, [len(self.first)])
        self.assertEqual(first_id, second_id)
        self.assertEqual(first[0]['name'], 'CurrentNode')
        self.assertEqual(first[0]['models'], ['part.stl'])
        self.assertEqual(second[0]['name'], 'RenamedNode')
        self.assertEqual(second[0]['models'], ['renamed/part.stl'])
        self.assertEqual(second[0]['count'], 1)

        record = json.loads(
            Path(pieces.fact_sidecar(self.artifact)).read_text())
        self.assertEqual(set(record), {
            'version', 'artifact', 'sha256', 'size', 'volume', 'watertight'})
        for forbidden in ('name', 'sources', 'models', 'count', 'hierarchy',
                          'placements', 'drivers', 'expressions', 'document'):
            self.assertNotIn(forbidden, record)

    def test_fresh_process_reuses_record_without_mesh_decode(self):
        marker = self.root / 'decodes'
        script = """
import os
from solid_node.core import pieces
class Node:
    stl_file = os.environ['ARTIFACT']
    src = os.environ['ARTIFACT']
    def _up_to_date(self, path): return True
real = pieces._geometry_facts_from_bytes
def counted(path, data):
    with open(os.environ['MARKER'], 'a') as output: output.write('decode\\n')
    return real(path, data)
pieces._geometry_facts_from_bytes = counted
with pieces.PieceInventory() as inventory:
    inventory.register(Node(), 'part.stl')
    print(json.dumps(inventory.pieces()[0]['size']))
"""
        environment = dict(os.environ, ARTIFACT=str(self.artifact),
                           MARKER=str(marker), PYTHONPATH=str(Path.cwd()))
        # json is deliberately imported in the child prefix rather than from
        # parent state: this is a genuine fresh interpreter boundary.
        script = 'import json\n' + script
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, '-c', script], cwd=self.root,
                env=environment, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [1.0, 2.0, 3.0])
        self.assertEqual(marker.read_text().splitlines(), ['decode'])

    def test_hash_and_mesh_facts_receive_the_same_pinned_bytes(self):
        hashed = []
        decoded = []
        real_digest = pieces._digest_bytes
        real_geometry = pieces._geometry_facts_from_bytes
        with (patch.object(
                pieces, '_digest_bytes',
                side_effect=lambda data: (hashed.append(data),
                                          real_digest(data))[1]),
              patch.object(
                pieces, '_geometry_facts_from_bytes',
                side_effect=lambda path, data: (decoded.append(data),
                                                real_geometry(path, data))[1])):
            identity, _ = self.register()
        self.assertEqual(hashed, [self.first])
        self.assertEqual(decoded, [self.first])
        self.assertEqual(identity, hashlib.sha256(self.first).hexdigest()[:12])

    def test_same_size_restored_mtime_replacement_recomputes(self):
        first_id, first = self.register()
        old_mtime = self.artifact.stat().st_mtime_ns
        replacement = self.root / 'replacement.stl'
        replacement.write_bytes(self.second)
        os.utime(replacement, ns=(old_mtime, old_mtime))
        os.replace(replacement, self.artifact)

        second_id, second = self.register()

        self.assertNotEqual(first_id, second_id)
        self.assertEqual(first[0]['size'], [1.0, 2.0, 3.0])
        self.assertEqual(second[0]['size'], [4.0, 5.0, 6.0])
        record = json.loads(Path(pieces.fact_sidecar(self.artifact)).read_text())
        self.assertEqual(record['sha256'], hashlib.sha256(self.second).hexdigest())

    def test_fresh_process_rejects_replaced_artifact_record(self):
        self.register()
        old_mtime = self.artifact.stat().st_mtime_ns
        replacement = self.root / 'replacement.stl'
        replacement.write_bytes(self.second)
        os.utime(replacement, ns=(old_mtime, old_mtime))
        os.replace(replacement, self.artifact)
        script = """
import json, os
from solid_node.core import pieces
class Node:
    stl_file = os.environ['ARTIFACT']
    src = os.environ['ARTIFACT']
    def _up_to_date(self, path): return True
with pieces.PieceInventory() as inventory:
    identity = inventory.register(Node(), 'part.stl')
    print(json.dumps([identity, inventory.pieces()[0]['size']]))
"""
        result = subprocess.run(
            [sys.executable, '-c', script], cwd=self.root,
            env=dict(os.environ, ARTIFACT=str(self.artifact),
                     PYTHONPATH=str(Path.cwd())),
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        identity, size = json.loads(result.stdout)
        self.assertEqual(identity, hashlib.sha256(self.second).hexdigest()[:12])
        self.assertEqual(size, [4.0, 5.0, 6.0])

    def test_missing_malformed_unknown_and_incomplete_records_recompute(self):
        record_path = Path(pieces.fact_sidecar(self.artifact))
        self.register()
        valid = json.loads(record_path.read_text())
        invalid = (
            None,
            b'{not-json',
            json.dumps({**valid, 'version': 999}).encode(),
            json.dumps({**valid, 'version': True}).encode(),
            json.dumps({**valid, 'artifact': {}}).encode(),
            json.dumps({**valid, 'size': [-1, 2, 3]}).encode(),
            json.dumps({key: value for key, value in valid.items()
                        if key != 'sha256'}).encode(),
        )
        real = pieces._geometry_facts_from_bytes
        for content in invalid:
            with self.subTest(content=content):
                record_path.unlink(missing_ok=True)
                if content is not None:
                    record_path.write_bytes(content)
                calls = []
                with patch.object(
                        pieces, '_geometry_facts_from_bytes',
                        side_effect=lambda path, data: (
                            calls.append(path), real(path, data))[1]):
                    self.register()
                self.assertEqual(calls, [str(self.artifact)])
                self.assertEqual(json.loads(record_path.read_text())['version'], 1)

    def test_unclosed_mesh_facts_are_persisted_honestly(self):
        mesh = trimesh.creation.box((1, 2, 3))
        mesh.faces = mesh.faces[:-1]
        self.artifact.write_bytes(mesh.export(file_type='stl'))
        _, first = self.register()
        with patch.object(
                pieces, '_geometry_facts_from_bytes',
                side_effect=AssertionError('valid facts should be reused')):
            _, second = self.register()
        self.assertFalse(first[0]['watertight'])
        self.assertFalse(second[0]['watertight'])

    def test_interrupted_record_publication_leaves_no_temporary_record(self):
        record = Path(pieces.fact_sidecar(self.artifact))
        with patch.object(pieces.os, 'replace', side_effect=OSError('stop')):
            identity, published = self.register()
        self.assertEqual(identity, hashlib.sha256(self.first).hexdigest()[:12])
        self.assertEqual(published[0]['size'], [1.0, 2.0, 3.0])
        self.assertFalse(record.exists())
        leftovers = list(self.root.glob(f'.{record.name}.*.tmp'))
        self.assertEqual(leftovers, [])
        with patch.object(
                pieces, '_geometry_facts_from_bytes',
                wraps=pieces._geometry_facts_from_bytes) as decode:
            self.register()
        decode.assert_called_once()

    def test_record_is_complete_before_atomic_replacement(self):
        record = Path(pieces.fact_sidecar(self.artifact))
        replaced = []
        real_replace = os.replace

        def inspect_then_replace(source, target):
            if target == str(record):
                candidate = json.loads(Path(source).read_text())
                self.assertEqual(candidate['version'], 1)
                self.assertEqual(candidate['sha256'],
                                 hashlib.sha256(self.first).hexdigest())
                self.assertEqual(candidate['size'], [1.0, 2.0, 3.0])
                replaced.append(True)
            return real_replace(source, target)

        with patch.object(pieces.os, 'replace', inspect_then_replace):
            self.register()
        self.assertEqual(replaced, [True])
        self.assertEqual(json.loads(record.read_text())['version'], 1)

    def test_public_prefix_collision_is_rejected_deterministically(self):
        other = self.root / 'other.stl'
        other.write_bytes(self.second)
        with patch.object(pieces, '_HASH_LEN', 0):
            with pieces.PieceInventory() as inventory:
                inventory.register(self.node, 'one.stl')
                with self.assertRaises(pieces.PieceIdCollisionError) as raised:
                    inventory.register(CurrentNode(other), 'two.stl')
        digests = sorted((hashlib.sha256(self.first).hexdigest(),
                          hashlib.sha256(self.second).hexdigest()))
        self.assertIn(digests[0], str(raised.exception))
        self.assertIn(digests[1], str(raised.exception))

    def test_context_closes_every_pinned_artifact(self):
        with pieces.PieceInventory() as inventory:
            inventory.register(self.node, 'part.stl')
            snapshots = list(inventory._snapshots.values())
            self.assertTrue(all(not snapshot.closed for snapshot in snapshots))
        self.assertTrue(all(snapshot.closed for snapshot in snapshots))


class LowerGeometryIdentityTest(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix='solid-lower-identity-')
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'part.stl'
        self.path.write_bytes(box_bytes((1, 2, 3)))
        base._base_mesh_cache.clear()
        test_module._bounds_cache.clear()
        test_module._manifold_cache.clear()
        test_module._verdict_cache.clear()
        test_module._verdict_observations.clear()

    def test_same_size_restored_mtime_invalidates_every_rigid_cache(self):
        old_mtime = self.path.stat().st_mtime_ns
        old_mesh = base.cached_base_mesh(str(self.path))
        old_bounds = test_module._cached_local_bounds(str(self.path))
        old_manifold, _, _ = test_module._cached_manifold(str(self.path))
        old_identity = test_module._geometry_identity(str(self.path))
        other = Path(self.temporary.name) / 'other.stl'
        other.write_bytes(box_bytes((1, 1, 1)))
        other_identity = test_module._geometry_identity(str(other))
        matrix = np.eye(4)
        old_key = test_module._verdict_key(
            old_identity, matrix, other_identity, matrix, 'faceted')
        self.assertEqual(test_module._memoized(old_key, lambda: 'old'), 'old')

        replacement = self.path.with_name('replacement.stl')
        replacement.write_bytes(box_bytes((4, 5, 6)))
        os.utime(replacement, ns=(old_mtime, old_mtime))
        os.replace(replacement, self.path)

        new_mesh = base.cached_base_mesh(str(self.path))
        new_bounds = test_module._cached_local_bounds(str(self.path))
        new_manifold, _, _ = test_module._cached_manifold(str(self.path))
        new_identity = test_module._geometry_identity(str(self.path))
        new_key = test_module._verdict_key(
            new_identity, matrix, other_identity, matrix, 'faceted')
        self.assertAlmostEqual(old_mesh.volume, 6.0, places=4)
        self.assertAlmostEqual(new_mesh.volume, 120.0, places=4)
        self.assertFalse(np.array_equal(old_bounds, new_bounds))
        self.assertNotEqual(old_identity, new_identity)
        self.assertIsNot(old_manifold, new_manifold)
        self.assertEqual(test_module._memoized(new_key, lambda: 'new'), 'new')

    def test_direct_verdict_cannot_be_cached_under_a_later_artifact(self):
        first_path = self.path
        first_path.write_bytes(box_bytes((1, 1, 1)))
        second_path = self.path.with_name('second.stl')
        second_path.write_bytes(box_bytes((1, 1, 1)))
        replacement = self.path.with_name('replacement.stl')
        replacement.write_bytes(box_bytes((10, 10, 10)))
        first = GeometryNode('first', first_path)
        second = GeometryNode('second', second_path, (3, 0, 0))
        real_fast = test_module._fast_geometry
        replaced = []

        def replace_after_first_lookup(node, compose_matrix):
            geometry = real_fast(node, compose_matrix)
            if node is first and not replaced:
                os.replace(replacement, first_path)
                replaced.append(True)
            return geometry

        with patch.object(test_module, '_fast_geometry',
                          replace_after_first_lookup):
            raced = test_module._engine_intersection_stats(
                first, second, lambda node: node.matrix)
        repeated = test_module._engine_intersection_stats(
            first, second, lambda node: node.matrix)
        test_module._verdict_cache.clear()
        current = test_module._engine_intersection_stats(
            first, second, lambda node: node.matrix)

        self.assertTrue(raced.is_empty)
        self.assertFalse(repeated.is_empty)
        self.assertAlmostEqual(repeated.volume, 1.0, places=4)
        self.assertEqual(repeated, current)

    def test_placement_bounds_and_deferred_manifold_share_one_identity(self):
        first_path = self.path
        first_path.write_bytes(box_bytes((1, 1, 1)))
        second_path = self.path.with_name('second.stl')
        second_path.write_bytes(box_bytes((1, 1, 1)))
        replacement = self.path.with_name('replacement.stl')
        replacement.write_bytes(box_bytes((10, 10, 10)))
        first = GeometryNode('first', first_path)
        second = GeometryNode('second', second_path, (3, 0, 0))
        assembly = GeometryAssembly([first, second])
        old_identity = test_module._geometry_identity(str(first_path))
        real_geometry = test_module._solid_geometry
        replaced = []

        def replace_after_first_bounds(node):
            geometry = real_geometry(node)
            if node is first and not replaced:
                os.replace(replacement, first_path)
                replaced.append(True)
            return geometry

        with (patch.object(test_module, '_solid_geometry',
                           replace_after_first_bounds),
              patch.object(test_module, '_compose_world_matrix',
                           side_effect=lambda node: node.matrix)):
            raced = test_module._placed_assembly_solids(assembly)

        self.assertEqual(raced[0][4], old_identity)
        self.assertEqual(list(test_module._bounds_candidates(
            [record[2] for record in raced])), [])
        self.assertAlmostEqual(test_module._placed_manifold(
            raced[0], 'test', 'test').volume(), 1.0, places=4)

        with patch.object(test_module, '_compose_world_matrix',
                          side_effect=lambda node: node.matrix):
            current = test_module._placed_assembly_solids(assembly)
        self.assertNotEqual(current[0][4], old_identity)
        self.assertEqual(list(test_module._bounds_candidates(
            [record[2] for record in current])), [(0, 1)])
        self.assertFalse(test_module._placed_intersection(
            current[0], current[1]).is_empty)


class CoherentExportTest(TestCase):
    def test_concurrent_replacement_retries_one_whole_inventory(self):
        temporary = tempfile.TemporaryDirectory(prefix='solid-export-race-')
        self.addCleanup(temporary.cleanup)
        build = Path(temporary.name) / '_build'
        output = Path(temporary.name) / 'export'
        node = Cube(str(build))
        old = Path(node.stl_file).read_bytes()
        new = b'SOLID cube\nENDSOLID cube\n'
        self.assertEqual(len(old), len(new))
        old_mtime = Path(node.stl_file).stat().st_mtime_ns
        real_copy = ArtifactSnapshot.copy_to
        replaced = []

        def racing_copy(snapshot, target):
            if not replaced:
                replacement = Path(node.stl_file).with_suffix('.new')
                replacement.write_bytes(new)
                os.utime(replacement, ns=(old_mtime, old_mtime))
                os.replace(replacement, node.stl_file)
                replaced.append(True)
            return real_copy(snapshot, target)

        with (patch.dict(os.environ, {'SOLID_BUILD_DIR': str(build)}),
              patch.object(node, 'build_stls'),
              patch.object(ArtifactSnapshot, 'copy_to', racing_copy)):
            manifest = export_node(node, str(output), widget=False)

        exported = (output / manifest['root']['model']).read_bytes()
        self.assertEqual(exported, new)
        self.assertEqual(manifest['root']['piece'],
                         hashlib.sha256(new).hexdigest()[:12])


class PieceFactSweepTest(TestCase):
    def test_fact_record_is_removed_with_its_unreferenced_artifact(self):
        temporary = tempfile.TemporaryDirectory(prefix='solid-fact-sweep-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        current = root / 'current.stl'
        stale = root / 'stale.stl'
        current.write_bytes(box_bytes((1, 2, 3)))
        stale.write_bytes(box_bytes((4, 5, 6)))
        with pieces.PieceInventory() as inventory:
            inventory.register(CurrentNode(stale), 'stale.stl')
        self.assertTrue(Path(pieces.fact_sidecar(stale)).exists())
        builder = Builder('model.py', build_dir=str(root), watch=False)
        builder.node = CurrentNode(current)
        builder.node.name = 'current'
        builder.node.rigid = True
        builder.node._type = 'SolidNode'
        builder.node.color = None
        builder.node.mtime = 0
        builder.node.operations = ()
        builder._write_viewer_snapshot()
        self.assertFalse(stale.exists())
        self.assertFalse(Path(pieces.fact_sidecar(stale)).exists())

    def test_exhausted_builder_retries_do_not_clear_a_previous_error(self):
        temporary = tempfile.TemporaryDirectory(prefix='solid-fact-retry-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        artifact = root / 'part.stl'
        artifact.write_bytes(box_bytes((1, 2, 3)))
        node = CurrentNode(artifact)
        node.name = 'part'
        node.rigid = True
        node._type = 'SolidNode'
        node.color = None
        node.mtime = 0
        node.operations = ()
        builder = Builder('model.py', build_dir=str(root), watch=False)
        builder.node = node
        write_error('previous', str(root))

        with patch.object(
                pieces.PieceInventory, 'validate',
                side_effect=ArtifactChanged('moving')) as validate:
            with self.assertRaisesRegex(ArtifactChanged, 'moving'):
                builder._write_viewer_snapshot()

        self.assertEqual(validate.call_count, 3)
        with open(root / 'errors.json') as stream:
            self.assertEqual(json.load(stream)['error'], 'previous')
        self.assertFalse((root / 'viewer.json').exists())
