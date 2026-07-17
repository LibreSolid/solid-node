# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import itertools
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
    # Perturbation assertions: torque-fit contracts
    #
    # Both share the same mechanic: a Rotation by a signed angle is
    # inserted into node.operations right before node's first
    # Translation (so it turns node about its OWN axis, the way a
    # part spins in its own bore/pocket, not around the world
    # origin), appended if node has no Translation. It is always
    # removed afterwards, success or failure, leaving node.operations
    # exactly as found.

    def assertBlockedBeyond(self, node, angle, against, axis=(0, 0, 1),
                            volume_epsilon=0.0):
        """Torque-fit engagement contract: perturbed by `angle`
        degrees about `axis`, in BOTH directions (+angle and -angle,
        checked separately), `node` must intersect `against` in every
        direction -- the fit must genuinely lock beyond its play.

        `volume_epsilon` (mm^3, default 0.0 keeps exact `is_empty`
        strictness): when > 0, a rotation only counts as blocked if
        the fouling volume exceeds `volume_epsilon` -- so a flush
        contact that produces boolean noise (see
        assertNoPairwiseIntersections) never masquerades as a genuine
        lock in either direction.
        """
        for signed_angle in (angle, -angle):
            self._assert_perturbation(
                node, signed_angle, against, axis, expect_intersect=True,
                volume_epsilon=volume_epsilon)

    def assertFreeWithin(self, node, angle, against, axis=(0, 0, 1),
                         volume_epsilon=0.0):
        """Anti-gaming twin of assertBlockedBeyond: perturbed by
        `angle` degrees (or every angle in a list/tuple, e.g. a
        journal/freewheel sweep), in BOTH directions, `node` must NOT
        intersect `against` -- so a blocking test elsewhere cannot be
        gamed by an oversized bore/pocket that never truly touches.

        `volume_epsilon` (mm^3, default 0.0 keeps exact `is_empty`
        strictness): when > 0, a rotation only counts as fouling if
        its volume exceeds `volume_epsilon`, so flush contact within
        the play window (boolean noise, not real engagement) does not
        wrongly fail this assertion.
        """
        angles = angle if isinstance(angle, (list, tuple)) else [angle]
        for one_angle in angles:
            for signed_angle in (one_angle, -one_angle):
                self._assert_perturbation(
                    node, signed_angle, against, axis, expect_intersect=False,
                    volume_epsilon=volume_epsilon)

    def _assert_perturbation(self, node, signed_angle, against, axis,
                             expect_intersect, volume_epsilon=0.0):
        operation = Rotation(signed_angle, list(axis), node)
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
                        f"{node.name} should be blocked at {signed_angle}deg "
                        f"against {against.name} (no intersection)")
                raise AssertionError(
                    f"{node.name} should be blocked at {signed_angle}deg "
                    f"against {against.name} (intersection volume {volume} "
                    f"does not exceed epsilon {volume_epsilon})")
            if not expect_intersect and is_fouling:
                message = (
                    f"{node.name} should be free at {signed_angle}deg "
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
