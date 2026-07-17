# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import itertools
import math
import re
import trimesh
from unittest import TestCase as BaseTestCase

from solid_node.node.operations import Rotation, Translation


class TestCase(BaseTestCase):

    def set_node(self, node):
        """This sets the "node" property on the test, and also an alias
        matching the class name, for testing convenience.
        """
        self.node = node

        # Set an alias convert CamelCase class to snake_case attribute
        attr_name = re.sub(
            r'(?<=[a-z])(?=[A-Z])', '_',
            self.__class__.__name__,
        ).lower().replace('_test', '')

        setattr(self, attr_name, node)

    ########################################
    # Assertion methods for mesh operations
    #

    def assertNotIntersecting(self, node1, node2):
        """Test that node1 and node 2 do not intersect"""
        intersection = trimesh.boolean.intersection([node1.mesh, node2.mesh])
        if not intersection.is_empty:
            raise AssertionError(
                f"{node1.name} should not intersect {node2.name} "
                f"(intersection volume {intersection.volume})"
            )

    def assertIntersecting(self, node1, node2):
        """Make sure node1 and node1 have some intersection"""
        intersection = node1.mesh.intersection(node2.mesh)
        if intersection.is_empty:
            raise AssertionError(
                f"{node1.name} should intersect {node2.name}")

    def assertInside(self, node1, node2):
        """Make sure node2 is completely inside node1"""
        inside = node1.mesh.contains(node2.mesh.vertices)
        if not inside.all():
            raise AssertionError(
                f"All vertices of {node2.name} should be inside {node1.name}")

    def assertClose(self, node1, node2, max_distance):
        """Make sure the distance of node1 to node2 is lesser than max_distance"""
        closest_points = trimesh.proximity.closest_point(
            node1.mesh, node2.mesh.vertices)
        distances = closest_points[1]
        if not (distances <= max_distance).all():
            raise AssertionError(
                f"All points of {node2.name} should be at most "
                f"{max_distance} units away from {node1.name}")

    def assertFar(self, node1, node2, min_distance):
        """Make sure the distance of node1 to node2 is greater than min_distance"""
        closest_points = trimesh.proximity.closest_point(
            node1.mesh, node2.mesh.vertices)
        distances = closest_points[1]
        if not (distances >= min_distance).all():
            raise AssertionError(
                f"All points of {node2.name} should be at least "
                f"{min_distance} units away from {node1.name}")

    def assertIntersectVolumeAbove(self, node1, node2, min_volume):
        """Make sure the volume of the intersection between node1 and node2
        is greater than min_volume.
        """
        intersection = node1.mesh.intersection(node2.mesh)
        if intersection.volume < min_volume:
            raise AssertionError(
                f"The intersection volume of {node1.name} and {node2.name} "
                f"should be above {min_volume}")

    def assertIntersectVolumeBelow(self, node1, node2, max_volume):
        """Make sure the volume of the intersection between node1 and node2
        is lesser than max_volume.
        """
        intersection = node1.mesh.intersection(node2.mesh)
        if intersection.volume > max_volume:
            raise AssertionError(
                f"The intersection volume of {node1.name} and {node2.name} "
                f"should be below {max_volume}")

    ########################################
    # Perturbation assertions: torque-fit / linear-stop contracts
    #
    # Both share the same mechanic and come in two mutually exclusive
    # modes, selected by which of `axis` (rotation, the default) or
    # `along` (translation) is given -- passing both is a loud error.
    # A Rotation (by a signed angle, about `axis`) or a Translation
    # (by a signed distance along the unit vector `along`) is
    # inserted into node.operations right before node's first
    # pre-existing Translation, appended if node has no Translation.
    #
    # That single insertion rule is what makes both modes "local":
    # a rotation turns node about its OWN axis rather than the world
    # origin, because it runs before node has been moved away from
    # the origin by its own placement Translation; a translation
    # likewise moves node along `along` in whatever frame node is in
    # at that point in its OWN operations -- so any Rotation that is
    # already part of node's own placement, or of an ancestor
    # assembly's, and therefore applies to the mesh AFTER this
    # insertion point, carries the perturbation's direction along
    # with it. `along` is a direction in node's local, pre-placement
    # frame, not a fixed world vector -- that carrying is the point.
    #
    # The perturbation is always removed afterwards, success or
    # failure, leaving node.operations exactly as found.

    def assertBlockedBeyond(self, node, angle, against, axis=None,
                            volume_epsilon=0.0, along=None,
                            directions='both'):
        """Torque-fit / linear-stop engagement contract: perturbed by
        `angle` degrees about `axis` (rotation mode, the default,
        axis=(0, 0, 1) when omitted) or by `angle` mm along the unit
        vector `along` (translation mode -- give one selector or the
        other, never both), `node` must intersect `against` -- the
        fit must genuinely lock beyond its play. See the class
        comment above for the local-frame semantics shared by both
        modes.

        `directions` (default 'both') checks +angle and -angle
        separately, and BOTH must foul. 'forward' checks only
        +angle -- for contracts that are deliberately one-sided (e.g.
        a sleeve blocked sliding inward by a lip, but free to slide
        outward). Any other value is a loud error.

        `volume_epsilon` (mm^3, default 0.0 keeps exact `is_empty`
        strictness): when > 0, a perturbation only counts as blocked
        if the fouling volume exceeds `volume_epsilon` -- so a flush
        contact that produces boolean noise (see
        assertNoPairwiseIntersections) never masquerades as a genuine
        lock in either direction.
        """
        axis, along, unit_along = self._resolve_perturbation_axis(axis, along)
        for signed_value in self._signed_perturbations(angle, directions):
            self._assert_perturbation(
                node, signed_value, against, axis, along, unit_along,
                expect_intersect=True, volume_epsilon=volume_epsilon)

    def assertFreeWithin(self, node, angle, against, axis=None,
                         volume_epsilon=0.0, along=None, directions='both'):
        """Anti-gaming twin of assertBlockedBeyond: perturbed by
        `angle` degrees about `axis` (rotation mode, the default) or
        by `angle` mm along the unit vector `along` (translation
        mode -- give one selector or the other, never both), `node`
        must NOT intersect `against` -- so a blocking test elsewhere
        cannot be gamed by an oversized bore/pocket/sleeve that never
        truly touches. `angle` accepts a list/tuple in either mode
        (e.g. a journal/freewheel sweep of angles, or a set of
        clearance distances), each checked in turn. See the class
        comment above for the local-frame semantics shared by both
        modes.

        `directions` (default 'both') checks +angle and -angle
        separately, and NEITHER may foul. 'forward' checks only
        +angle -- for contracts that are deliberately one-sided. Any
        other value is a loud error.

        `volume_epsilon` (mm^3, default 0.0 keeps exact `is_empty`
        strictness): when > 0, a perturbation only counts as fouling
        if its volume exceeds `volume_epsilon`, so flush contact
        within the play window (boolean noise, not real engagement)
        does not wrongly fail this assertion.
        """
        axis, along, unit_along = self._resolve_perturbation_axis(axis, along)
        angles = angle if isinstance(angle, (list, tuple)) else [angle]
        for one_angle in angles:
            for signed_value in self._signed_perturbations(
                    one_angle, directions):
                self._assert_perturbation(
                    node, signed_value, against, axis, along, unit_along,
                    expect_intersect=False, volume_epsilon=volume_epsilon)

    def _resolve_perturbation_axis(self, axis, along):
        """Resolves the axis/along selector into one of the two
        mutually exclusive perturbation modes. Returns (axis, along,
        unit_along): rotation mode has axis set and along/unit_along
        None; translation mode has along/unit_along set (the
        original vector, and its normalized unit form used for the
        actual displacement) and axis None."""
        if axis is not None and along is not None:
            raise ValueError(
                "assertBlockedBeyond/assertFreeWithin: pass axis "
                "(rotation) or along (translation), not both")
        if along is not None:
            vector = list(along)
            magnitude = math.sqrt(sum(component * component
                                      for component in vector))
            if magnitude == 0:
                raise ValueError(
                    "assertBlockedBeyond/assertFreeWithin: along must "
                    "be a nonzero vector")
            unit_along = [component / magnitude for component in vector]
            return None, vector, unit_along
        return (axis if axis is not None else (0, 0, 1)), None, None

    def _signed_perturbations(self, value, directions):
        """The signed values to check for one magnitude (angle or
        distance), per `directions`."""
        if directions == 'both':
            return (value, -value)
        if directions == 'forward':
            return (value,)
        raise ValueError(
            "assertBlockedBeyond/assertFreeWithin: directions must be "
            f"'both' or 'forward', got {directions!r}")

    def _assert_perturbation(self, node, signed_value, against, axis, along,
                             unit_along, expect_intersect,
                             volume_epsilon=0.0):
        if unit_along is not None:
            operation = Translation(
                [signed_value * component for component in unit_along],
                node)
            label = f"displaced {signed_value}mm along {along}"
        else:
            operation = Rotation(signed_value, list(axis), node)
            label = f"at {signed_value}deg"
        index = next(
            (i for i, op in enumerate(node.operations)
             if isinstance(op, Translation)),
            len(node.operations),
        )
        node.operations.insert(index, operation)
        try:
            intersection = trimesh.boolean.intersection(
                [node.mesh, against.mesh])
            volume = 0.0 if intersection.is_empty else intersection.volume
            is_fouling = (
                not intersection.is_empty if volume_epsilon <= 0
                else abs(volume) > volume_epsilon)
            if expect_intersect and not is_fouling:
                if intersection.is_empty:
                    raise AssertionError(
                        f"{node.name} should be blocked {label} "
                        f"against {against.name} (no intersection)")
                raise AssertionError(
                    f"{node.name} should be blocked {label} "
                    f"against {against.name} (intersection volume {volume} "
                    f"does not exceed epsilon {volume_epsilon})")
            if not expect_intersect and is_fouling:
                message = (
                    f"{node.name} should be free {label} "
                    f"against {against.name} "
                    f"(intersection volume {volume})")
                if volume_epsilon > 0:
                    message += f", exceeds epsilon {volume_epsilon}"
                raise AssertionError(message)
        finally:
            node.operations.remove(operation)

    ########################################
    # Adjacency sweep

    def assertNoPairwiseIntersections(self, node, volume_epsilon=0.0):
        """Walk the assembled tree rooted at `node` down to its
        leaves (a node with no children is a leaf; every other node's
        children are walked recursively) and assert that every pair
        of leaves is non-intersecting. The safety net that holds
        regardless of which specific contracts exist: any two parts
        someone forgot to test against each other directly are still
        covered here.

        `volume_epsilon` (mm^3, default 0.0 keeps exact `is_empty`
        strictness): two parts that legitimately abut flush (e.g.
        shaft segments whose end faces meet exactly) can produce a
        non-empty boolean of pure float noise -- a sliver mesh with
        volume on the order of 1e-13 mm^3, indistinguishable to
        `is_empty` from real interference. When `volume_epsilon > 0`,
        an intersection only counts as real interference if its
        volume exceeds `volume_epsilon`; a genuine overlap comfortably
        above the epsilon is still reported.
        """
        leaves = self._leaves(node)
        for leaf1, leaf2 in itertools.combinations(leaves, 2):
            intersection = trimesh.boolean.intersection(
                [leaf1.mesh, leaf2.mesh])
            if intersection.is_empty:
                continue
            volume = intersection.volume
            if volume_epsilon > 0 and abs(volume) <= volume_epsilon:
                continue
            message = (
                f"{leaf1.name} should not intersect {leaf2.name} "
                f"(intersection volume {volume})")
            if volume_epsilon > 0:
                message += f", exceeds epsilon {volume_epsilon}"
            raise AssertionError(message)

    def _leaves(self, node):
        """All leaf nodes of the assembled tree rooted at node."""
        if not node.children:
            return [node]
        leaves = []
        for child in node.children:
            leaves.extend(self._leaves(child))
        return leaves


class TestCaseMixin(TestCase):
    """For convenience, nodes can inherit TestCaseMixin to implement
    tests together with rendering logic.
    """
    def set_node(self, node):
        """Override TestCase setup, self and node are the same"""
        pass


def testing_instant(instant):
    """Use this decorator on a test to define a specific instant
    of the animation that should be used to run the test
    """
    def decorator(method):
        method.testing_instants = [instant]
        return method

    return decorator


def testing_steps(steps, start=0, end=1):
    """Use this decorator to run the test in several steps
    of the animation. Use start and end to define the range
    in that will be divided in those steps.
    """
    if steps < 2:
        raise AssertionError("Expected at least 2 steps, "
                             "for single step use @testing_instant instead"
                             )

    duration = end - start
    step = duration / (steps - 1)
    instants = [ start + i * step for i in range(steps) ]
    instants[-1] = end

    def decorator(method):
        method.testing_instants = instants
        return method

    return decorator
