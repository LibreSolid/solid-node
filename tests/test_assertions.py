# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the perturbation assertions' mechanics
(assertBlockedBeyond/assertFreeWithin, issue #6) -- the parts the
meta-test harness cannot see precisely, because it only observes
green/red through a subprocess. These build tiny stand-ins with REAL
Rotation/Translation operations lists, and a .mesh property that
composes them onto a base box the way AbstractBaseNode.mesh does,
without needing an actual STL build.
"""

from unittest import TestCase
from trimesh.creation import box

from solid_node.node.operations import Rotation, Translation
from solid_node.test import TestCase as AssertingTestCase


asserter = AssertingTestCase()


class FakeNode:
    """Minimal stand-in for AbstractBaseNode: a real .operations list
    (the assertions insert/remove real Rotation instances into it),
    and a .mesh property that applies those operations to a base
    unit box, mirroring AbstractBaseNode.mesh's composition."""

    def __init__(self, name='Node', size=1.0):
        self.name = name
        self.operations = []
        self._size = size

    def as_number(self, n):
        return float(n)

    @property
    def mesh(self):
        mesh = box((self._size,) * 3)
        for operation in self.operations:
            operation.mesh(mesh)
        return mesh


class RecordingNode(FakeNode):
    """Records a snapshot of its own operations list every time its
    mesh is accessed -- lets a test see exactly what the assertion
    inserted, and where, at the moment the boolean check ran."""

    def __init__(self, name='Node', size=1.0):
        super().__init__(name, size)
        self.recorded = []

    @property
    def mesh(self):
        self.recorded.append(list(self.operations))
        return FakeNode.mesh.fget(self)


class FarAway(FakeNode):
    """An `against` that never truly intersects anything: for tests
    that only care about the perturbation mechanics, not geometry."""

    def __init__(self, name='Against'):
        super().__init__(name)

    @property
    def mesh(self):
        mesh = FakeNode.mesh.fget(self)
        mesh.apply_translation([1000, 1000, 1000])
        return mesh


class CountingFarAway(FarAway):
    """Same as FarAway, but counts how many times its mesh was
    accessed -- for asserting every angle of a list was checked."""

    def __init__(self, name='Against'):
        super().__init__(name)
        self.calls = 0

    @property
    def mesh(self):
        self.calls += 1
        return FarAway.mesh.fget(self)


class IntersectsWhenPositive:
    """An `against` whose mesh overlaps `node`'s box only while
    node's current Rotation has a POSITIVE angle -- lets a test prove
    the negative direction is genuinely, separately checked."""

    def __init__(self, node, name='Against'):
        self._node = node
        self.name = name

    @property
    def mesh(self):
        rotations = [op for op in self._node.operations
                     if isinstance(op, Rotation)]
        angle = rotations[0].angle if rotations else 0
        mesh = box((1, 1, 1))
        if angle <= 0:
            mesh.apply_translation([1000, 1000, 1000])
        return mesh


class IntersectsWhenNegative(IntersectsWhenPositive):
    """Mirror of IntersectsWhenPositive: overlaps only while node's
    current Rotation has a NEGATIVE angle."""

    @property
    def mesh(self):
        rotations = [op for op in self._node.operations
                     if isinstance(op, Rotation)]
        angle = rotations[0].angle if rotations else 0
        mesh = box((1, 1, 1))
        if angle >= 0:
            mesh.apply_translation([1000, 1000, 1000])
        return mesh


class PerturbationInsertionTest(TestCase):

    def test_rotation_inserted_before_first_translation(self):
        node = RecordingNode()
        placement = Translation([5, 0, 0], node)
        node.operations.append(placement)
        against = FarAway()

        asserter.assertFreeWithin(node, 1.0, against)

        # Both signed directions (+1.0 and -1.0) get a snapshot; each
        # must show the Rotation sitting BEFORE the pre-existing
        # Translation, never after it.
        self.assertEqual(len(node.recorded), 2)
        for operations in node.recorded:
            self.assertEqual(len(operations), 2)
            self.assertIsInstance(operations[0], Rotation)
            self.assertIs(operations[1], placement)

    def test_rotation_appended_when_no_translation_present(self):
        node = RecordingNode()
        against = FarAway()

        asserter.assertFreeWithin(node, 1.0, against)

        self.assertEqual(len(node.recorded), 2)
        for operations in node.recorded:
            self.assertEqual(len(operations), 1)
            self.assertIsInstance(operations[0], Rotation)


class OperationsRestoredTest(TestCase):

    def test_restored_after_success(self):
        node = FakeNode()
        placement = Translation([0, 0, 0], node)
        node.operations.append(placement)
        # A same-sized, same-position against always overlaps,
        # whatever the rotation: both directions genuinely block.
        against = FakeNode('Against')

        asserter.assertBlockedBeyond(node, 10, against)

        self.assertEqual(node.operations, [placement])

    def test_restored_after_failure(self):
        node = FakeNode()
        placement = Translation([0, 0, 0], node)
        node.operations.append(placement)
        against = IntersectsWhenPositive(node)

        with self.assertRaises(AssertionError):
            asserter.assertBlockedBeyond(node, 10, against)

        self.assertEqual(node.operations, [placement])


class BothDirectionsCheckedTest(TestCase):

    def test_assert_blocked_beyond_fails_when_only_one_direction_blocks(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = IntersectsWhenPositive(node, name='Slot')

        with self.assertRaises(AssertionError) as ctx:
            asserter.assertBlockedBeyond(node, 10, against)

        message = str(ctx.exception)
        self.assertIn('Peg', message)
        self.assertIn('Slot', message)
        self.assertIn('-10', message)
        self.assertIn('no intersection', message)

    def test_assert_free_within_fails_when_only_one_direction_frees(self):
        # If the negative direction were not actually checked, this
        # setup (which only fouls for negative angles) would wrongly
        # be reported free.
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = IntersectsWhenNegative(node, name='Slot')

        with self.assertRaises(AssertionError) as ctx:
            asserter.assertFreeWithin(node, 5, against)

        message = str(ctx.exception)
        self.assertIn('Peg', message)
        self.assertIn('Slot', message)
        self.assertIn('-5', message)


class FreeWithinAngleListTest(TestCase):

    def test_accepts_a_list_of_angles_and_checks_every_one(self):
        node = FakeNode()
        node.operations.append(Translation([0, 0, 0], node))
        against = CountingFarAway()

        asserter.assertFreeWithin(node, [5, 10, 15], against)

        # 3 angles, each in both directions.
        self.assertEqual(against.calls, 6)


class FixedVolumeOverlap:
    """An `against` whose overlap with `node`'s unit box is a CONSTANT
    volume regardless of node's rotation about Z: a big-footprint
    (10x10) box, so node's rotated 1x1 footprint is always fully
    contained in X/Y, stacked so it only overlaps a `z_overlap`-thick
    slab of node's Z extent -- rotation about Z never changes a
    point's Z coordinate, so this volume is exact and angle-
    independent. Lets volume_epsilon's threshold be tested precisely,
    without depending on real boolean-noise geometry."""

    def __init__(self, z_overlap, name='Against'):
        self.z_overlap = z_overlap
        self.name = name

    @property
    def mesh(self):
        mesh = box((10, 10, 1))
        # node's box spans z in [-0.5, 0.5]; this slab spans
        # [0.5 - z_overlap, 1.5 - z_overlap], overlapping node's box
        # in exactly [0.5 - z_overlap, 0.5] -- a z_overlap-thick slice
        # of node's 1x1 footprint, volume == z_overlap.
        mesh.apply_translation([0, 0, 1.0 - self.z_overlap])
        return mesh


class VolumeEpsilonPerturbationTest(TestCase):
    """volume_epsilon on assertBlockedBeyond/assertFreeWithin
    (skill-repo improvements.md #21): default 0.0 keeps exact
    `is_empty` strictness; above 0 a rotation only counts as fouling
    if its intersection volume exceeds the epsilon."""

    def test_default_epsilon_blocks_on_any_nonempty_intersection(self):
        """Unchanged behavior: a tiny (1e-4) but non-empty overlap
        still counts as blocked when volume_epsilon is left at its
        default 0.0."""
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = FixedVolumeOverlap(1e-4, name='Slot')

        asserter.assertBlockedBeyond(node, 10, against)

    def test_epsilon_above_noise_does_not_count_as_blocked(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = FixedVolumeOverlap(1e-4, name='Slot')

        with self.assertRaises(AssertionError) as ctx:
            asserter.assertBlockedBeyond(
                node, 10, against, volume_epsilon=1e-2)

        message = str(ctx.exception)
        self.assertIn('Peg', message)
        self.assertIn('Slot', message)
        self.assertIn('does not exceed epsilon', message)

    def test_epsilon_still_blocks_on_genuine_engagement(self):
        """A real engagement volume comfortably above the epsilon
        must still count as blocked -- epsilon must not defeat a
        genuine lock."""
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = FixedVolumeOverlap(0.5, name='Slot')

        asserter.assertBlockedBeyond(node, 10, against, volume_epsilon=1e-6)

    def test_default_epsilon_fails_free_on_any_nonempty_intersection(self):
        """Unchanged behavior: a tiny (1e-4) but non-empty overlap
        still fails assertFreeWithin when volume_epsilon is left at
        its default 0.0."""
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = FixedVolumeOverlap(1e-4, name='Slot')

        with self.assertRaises(AssertionError):
            asserter.assertFreeWithin(node, 5, against)

    def test_epsilon_above_noise_reads_as_free(self):
        node = FakeNode()
        node.operations.append(Translation([0, 0, 0], node))
        against = FixedVolumeOverlap(1e-4)

        asserter.assertFreeWithin(node, 5, against, volume_epsilon=1e-2)

    def test_epsilon_cannot_mask_a_real_foul(self):
        """Anti-gaming: a real, substantial overlap must still fail
        assertFreeWithin even with volume_epsilon in play."""
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = FixedVolumeOverlap(0.5, name='Slot')

        with self.assertRaises(AssertionError) as ctx:
            asserter.assertFreeWithin(node, 5, against, volume_epsilon=1e-6)

        message = str(ctx.exception)
        self.assertIn('Peg', message)
        self.assertIn('Slot', message)
        self.assertIn('exceeds epsilon', message)

    def test_operations_restored_after_epsilon_failure(self):
        node = FakeNode()
        placement = Translation([0, 0, 0], node)
        node.operations.append(placement)
        against = FixedVolumeOverlap(1e-4)

        with self.assertRaises(AssertionError):
            asserter.assertBlockedBeyond(
                node, 10, against, volume_epsilon=1e-2)

        self.assertEqual(node.operations, [placement])
