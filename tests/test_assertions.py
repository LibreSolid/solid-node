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
import trimesh
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


########################################
# Translational mode (skill-repo improvements.md #25): everything
# above this line covers the pre-existing rotational mode and is left
# untouched -- it doubles as the regression suite for the new
# axis=None/along=None signature (see RotationalModeRegressionTest
# below for two more, explicit, pins on that resolution).
#

class IntersectsWhenTranslationPositive:
    """Translation analogue of IntersectsWhenPositive. Unlike
    rotation about the origin, a translation genuinely relocates
    node's box away from the origin -- so, unlike IntersectsWhenPositive,
    this cannot just stay put and rely on approximate overlap: while
    node's current perturbation Translation has a POSITIVE first
    component, this places its OWN box at that exact destination (full
    overlap, at any magnitude); otherwise it moves far away. The
    perturbation Translation is always inserted before any pre-existing
    placement Translation (same insertion rule as rotation mode), so
    it is reliably the first Translation in node.operations."""

    def __init__(self, node, name='Against'):
        self._node = node
        self.name = name

    @property
    def mesh(self):
        translations = [op for op in self._node.operations
                        if isinstance(op, Translation)]
        vector = translations[0].translation if translations else [0, 0, 0]
        mesh = box((1, 1, 1))
        if vector[0] > 0:
            mesh.apply_translation(vector)
        else:
            mesh.apply_translation([1000, 1000, 1000])
        return mesh


class IntersectsWhenTranslationNegative(IntersectsWhenTranslationPositive):
    """Mirror of IntersectsWhenTranslationPositive: places itself at
    node's exact destination only while node's current perturbation
    Translation has a NEGATIVE first component."""

    @property
    def mesh(self):
        translations = [op for op in self._node.operations
                        if isinstance(op, Translation)]
        vector = translations[0].translation if translations else [0, 0, 0]
        mesh = box((1, 1, 1))
        if vector[0] < 0:
            mesh.apply_translation(vector)
        else:
            mesh.apply_translation([1000, 1000, 1000])
        return mesh


class TranslationalInsertionTest(TestCase):
    """Translation analogue of PerturbationInsertionTest: `along`
    inserts a Translation (not a Rotation) at the exact same point --
    right before node's first pre-existing Translation, appended if
    there is none."""

    def test_translation_inserted_before_first_translation(self):
        node = RecordingNode()
        placement = Translation([5, 0, 0], node)
        node.operations.append(placement)
        against = FarAway()

        asserter.assertFreeWithin(node, 1.0, against, along=(0, 1, 0))

        self.assertEqual(len(node.recorded), 2)
        for operations in node.recorded:
            self.assertEqual(len(operations), 2)
            self.assertIsInstance(operations[0], Translation)
            self.assertIsNot(operations[0], placement)
            self.assertIs(operations[1], placement)

    def test_translation_appended_when_no_translation_present(self):
        node = RecordingNode()
        against = FarAway()

        asserter.assertFreeWithin(node, 1.0, against, along=(0, 1, 0))

        self.assertEqual(len(node.recorded), 2)
        for operations in node.recorded:
            self.assertEqual(len(operations), 1)
            self.assertIsInstance(operations[0], Translation)


class TranslationalOperationsRestoredTest(TestCase):

    def test_restored_after_success(self):
        node = FakeNode()
        placement = Translation([0, 0, 0], node)
        node.operations.append(placement)
        # A same-sized, same-position against always overlaps,
        # whatever the displacement: both directions genuinely block.
        # (Unlike rotation, a translation genuinely relocates node --
        # a small distance, well inside the unit box's own half-size
        # of 0.5, keeps the overlap with a same-position against
        # unconditional.)
        against = FakeNode('Against')

        asserter.assertBlockedBeyond(node, 0.3, against, along=(1, 0, 0))

        self.assertEqual(node.operations, [placement])

    def test_restored_after_failure(self):
        node = FakeNode()
        placement = Translation([0, 0, 0], node)
        node.operations.append(placement)
        against = IntersectsWhenTranslationPositive(node)

        with self.assertRaises(AssertionError):
            asserter.assertBlockedBeyond(node, 10, against, along=(1, 0, 0))

        self.assertEqual(node.operations, [placement])


class TranslationalBothDirectionsCheckedTest(TestCase):

    def test_assert_blocked_beyond_fails_when_only_one_direction_blocks(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = IntersectsWhenTranslationPositive(node, name='Slot')

        with self.assertRaises(AssertionError) as ctx:
            asserter.assertBlockedBeyond(node, 10, against, along=(1, 0, 0))

        message = str(ctx.exception)
        self.assertIn('Peg', message)
        self.assertIn('Slot', message)
        self.assertIn('no intersection', message)
        self.assertIn('displaced', message)
        self.assertIn('along', message)

    def test_assert_free_within_fails_when_only_one_direction_frees(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = IntersectsWhenTranslationNegative(node, name='Slot')

        with self.assertRaises(AssertionError) as ctx:
            asserter.assertFreeWithin(node, 5, against, along=(1, 0, 0))

        message = str(ctx.exception)
        self.assertIn('Peg', message)
        self.assertIn('Slot', message)
        self.assertIn('displaced', message)


class TranslationalDistanceListTest(TestCase):

    def test_accepts_a_list_of_distances_and_checks_every_one(self):
        node = FakeNode()
        node.operations.append(Translation([0, 0, 0], node))
        against = CountingFarAway()

        asserter.assertFreeWithin(node, [1, 2, 3], against, along=(1, 0, 0))

        # 3 distances, each in both directions.
        self.assertEqual(against.calls, 6)


class TranslationalVolumeEpsilonTest(TestCase):
    """volume_epsilon in translation mode (skill-repo improvements.md
    #25): reuses the rotational epsilon tests' FixedVolumeOverlap
    fixture -- its overlap volume depends only on Z, so translating
    node along X (well within the 10-wide platform) leaves the
    measured volume exact, proving epsilon is honored identically in
    both modes without re-deriving a second noise-precision fixture."""

    def test_default_epsilon_blocks_on_any_nonempty_intersection(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = FixedVolumeOverlap(1e-4, name='Slot')

        asserter.assertBlockedBeyond(node, 1, against, along=(1, 0, 0))

    def test_epsilon_above_noise_does_not_count_as_blocked(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = FixedVolumeOverlap(1e-4, name='Slot')

        with self.assertRaises(AssertionError) as ctx:
            asserter.assertBlockedBeyond(
                node, 1, against, along=(1, 0, 0), volume_epsilon=1e-2)

        message = str(ctx.exception)
        self.assertIn('does not exceed epsilon', message)
        self.assertIn('displaced', message)

    def test_epsilon_cannot_mask_a_real_foul(self):
        """Anti-gaming: a real, substantial overlap must still fail
        assertFreeWithin even with volume_epsilon in play."""
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = FixedVolumeOverlap(0.5, name='Slot')

        with self.assertRaises(AssertionError) as ctx:
            asserter.assertFreeWithin(
                node, 1, against, along=(1, 0, 0), volume_epsilon=1e-6)

        message = str(ctx.exception)
        self.assertIn('exceeds epsilon', message)


class TranslationalDirectionsTest(TestCase):
    """`directions='forward'` (skill-repo improvements.md #25): a
    one-sided contract -- blocked one way, deliberately open the
    other, the sleeve-with-a-lip case from the ratified spec -- must
    pass under 'forward' and fail under the default 'both'."""

    def test_forward_passes_a_one_sided_blocked_contract(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = IntersectsWhenTranslationPositive(node, name='Slot')

        # Only +distance is checked, and it genuinely fouls.
        asserter.assertBlockedBeyond(
            node, 10, against, along=(1, 0, 0), directions='forward')

    def test_both_fails_the_same_one_sided_contract(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = IntersectsWhenTranslationPositive(node, name='Slot')

        with self.assertRaises(AssertionError):
            asserter.assertBlockedBeyond(
                node, 10, against, along=(1, 0, 0), directions='both')

    def test_forward_passes_a_one_sided_free_contract(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        # Fouls only in -distance; 'forward' never checks it.
        against = IntersectsWhenTranslationNegative(node, name='Slot')

        asserter.assertFreeWithin(
            node, 5, against, along=(1, 0, 0), directions='forward')

    def test_both_fails_the_same_one_sided_free_contract(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = IntersectsWhenTranslationNegative(node, name='Slot')

        with self.assertRaises(AssertionError):
            asserter.assertFreeWithin(
                node, 5, against, along=(1, 0, 0), directions='both')


class PerturbationModeValidationTest(TestCase):
    """Loud errors for the axis/along selector and the directions
    kwarg (skill-repo improvements.md #25), raised before any
    perturbation is inserted into node.operations."""

    def test_axis_and_along_together_is_a_loud_error(self):
        node = FakeNode()
        node.operations.append(Translation([0, 0, 0], node))
        against = FarAway()

        with self.assertRaises(ValueError):
            asserter.assertBlockedBeyond(
                node, 5, against, axis=(0, 0, 1), along=(1, 0, 0))

        self.assertEqual(len(node.operations), 1)

    def test_zero_along_is_a_loud_error(self):
        node = FakeNode()
        node.operations.append(Translation([0, 0, 0], node))
        against = FarAway()

        with self.assertRaises(ValueError):
            asserter.assertBlockedBeyond(node, 5, against, along=(0, 0, 0))

        self.assertEqual(len(node.operations), 1)

    def test_bad_directions_value_is_a_loud_error(self):
        node = FakeNode()
        node.operations.append(Translation([0, 0, 0], node))
        against = FarAway()

        with self.assertRaises(ValueError):
            asserter.assertBlockedBeyond(
                node, 5, against, directions='sideways')

        self.assertEqual(len(node.operations), 1)


class RotationalModeRegressionTest(TestCase):
    """axis=None -> (0, 0, 1) resolution (skill-repo improvements.md
    #25): the whole rotational-mode suite above this section already
    exercises the new signature's default (it never passes axis
    explicitly); these two pin the resolution directly, including the
    old hard default passed explicitly, which must behave
    identically."""

    def test_default_axis_still_resolves_to_z(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = FakeNode('Slot')  # always overlaps, whatever the angle

        asserter.assertBlockedBeyond(node, 10, against)

    def test_explicit_old_default_axis_behaves_identically(self):
        node = FakeNode(name='Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = FakeNode('Slot')

        asserter.assertBlockedBeyond(node, 10, against, axis=(0, 0, 1))


class LocalFrameCarriedByRotationTest(TestCase):
    """Pins the local-frame semantics (skill-repo improvements.md
    #25): a translational perturbation is inserted at the SAME point
    as a rotational one -- right before node's own first Translation
    -- so any Rotation that is already part of node's OWN placement
    and sits AFTER that insertion point (applied to the mesh after
    the perturbation, in node.mesh's left-to-right composition)
    carries the perturbation's direction along with it. `along` is
    therefore a direction in node's pre-placement LOCAL frame, not a
    fixed world vector.

    node's own operations are built as [Translation([5, 0, 0]),
    Rotation(90, Z)] -- i.e. node.translate(...) then node.rotate(...)
    were called in that order, a "place then spin about the world
    origin" placement. Without any perturbation this composes to a
    node centered at world (0, 5, 0) (R90 maps (5, 0, 0) -> (0, 5, 0)).
    A `along=(1, 0, 0)` perturbation of distance 1.5 is inserted
    before the placement Translation, i.e. BEFORE the placement
    Rotation runs too -- so the rotation carries it: the true world
    displacement is R90((1.5, 0, 0)) == (0, 1.5, 0), NOT the raw
    (1.5, 0, 0) a naive world-frame reading of `along` would predict.
    `against_correct` sits exactly at the carried destination (0, 6.5,
    0) and `against_naive` sits exactly at the un-carried, wrong
    destination (1.5, 5, 0) -- far enough from the real destination
    that there is no boundary-touching ambiguity either way. The two
    positions disagree on the verdict: this is the geometry the spec
    asks for."""

    DISTANCE = 1.5

    def _node(self):
        node = FakeNode(name='Node')
        node.operations.append(Translation([5, 0, 0], node))
        node.operations.append(Rotation(90, [0, 0, 1], node))
        return node

    def test_carried_destination_genuinely_fouls(self):
        node = self._node()
        against_correct = FakeNode('Correct')
        against_correct.operations.append(Translation([0, 6.5, 0],
                                                       against_correct))

        asserter.assertBlockedBeyond(
            node, self.DISTANCE, against_correct, along=(1, 0, 0),
            directions='forward')

    def test_naive_uncarried_destination_stays_clear(self):
        node = self._node()
        against_naive = FakeNode('Naive')
        against_naive.operations.append(Translation([1.5, 5, 0],
                                                     against_naive))

        asserter.assertFreeWithin(
            node, self.DISTANCE, against_naive, along=(1, 0, 0),
            directions='forward')


class Pin(FakeNode):
    """A cylindrical pin, standing in for node: same minimal
    operations/mesh contract as FakeNode, but a real cylinder (genuine
    trimesh geometry) instead of a box."""

    def __init__(self, radius, name='Pin'):
        super().__init__(name)
        self._radius = radius

    @property
    def mesh(self):
        mesh = trimesh.creation.cylinder(
            radius=self._radius, height=3, sections=64)
        for operation in self.operations:
            operation.mesh(mesh)
        return mesh


class Bore:
    """A real bore: a block with a cylindrical hole of `radius`
    through it, built with a genuine boolean difference (not a fudged
    stand-in), computed once since it does not depend on node's
    perturbation."""

    def __init__(self, radius, name='Bore'):
        self.name = name
        block = trimesh.creation.box((10, 10, 4))
        hole = trimesh.creation.cylinder(radius=radius, height=5, sections=64)
        self._mesh = trimesh.boolean.difference([block, hole])

    @property
    def mesh(self):
        return self._mesh


class TranslationalPinInBoreTest(TestCase):
    """A pin captured in a bore with a known radial clearance (skill-
    repo improvements.md #25's ratified green case): blocked well
    beyond the clearance, free well within it, both directions. Both
    pin and bore are axisymmetric about Z, so the clearance is exact
    whichever horizontal `along` direction is swept -- along=(1, 0, 0)
    stands in for the general case. The oversized-bore case
    (LOOSE_BORE_RADIUS) is the ratified failing case: an anti-gaming
    check that a pocket loose enough to never touch cannot pass as
    blocked."""

    PIN_RADIUS = 1.0
    BORE_RADIUS = 1.3          # 0.3mm radial clearance
    LOOSE_BORE_RADIUS = 2.3    # 1.3mm clearance: never fouls at BLOCKED

    BLOCKED = 0.5   # beyond the 0.3mm clearance: must foul, both directions
    FREE = 0.1      # well within the 0.3mm clearance: must clear, both directions

    def _pin(self):
        pin = Pin(self.PIN_RADIUS, name='Pin')
        pin.operations.append(Translation([0, 0, 0], pin))
        return pin

    def test_pin_blocked_beyond_clearance(self):
        bore = Bore(self.BORE_RADIUS, name='Bore')

        asserter.assertBlockedBeyond(
            self._pin(), self.BLOCKED, bore, along=(1, 0, 0))

    def test_pin_free_within_clearance(self):
        bore = Bore(self.BORE_RADIUS, name='Bore')

        asserter.assertFreeWithin(
            self._pin(), self.FREE, bore, along=(1, 0, 0))

    def test_oversized_bore_fails_the_blocked_contract(self):
        bore = Bore(self.LOOSE_BORE_RADIUS, name='Bore')

        with self.assertRaises(AssertionError) as ctx:
            asserter.assertBlockedBeyond(
                self._pin(), self.BLOCKED, bore, along=(1, 0, 0))

        message = str(ctx.exception)
        self.assertIn('Pin', message)
        self.assertIn('Bore', message)
        self.assertIn('displaced', message)
        self.assertIn('along', message)
        self.assertIn('no intersection', message)
