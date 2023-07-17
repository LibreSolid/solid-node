import re
import inspect
import trimesh
from unittest import TestCase as BaseTestCase
from solid_node.node.base import StlRenderStart




class TestCase(BaseTestCase):

    ########################################
    # Assertion methods for mesh operations
    #

    def assertNotIntersecting(self, node1, node2):
        intersection = trimesh.boolean.intersection([node1.mesh, node2.mesh])
        if not intersection.is_empty:
            raise AssertionError(
                f"{node1.name} should not intersect {node2.name}")

    def assertIntersecting(self, node1, node2):
        intersection = node1.mesh.intersection(node2.mesh)
        if intersection.is_empty:
            raise AssertionError(
                f"{node1.name} should intersect {node2.name}")

    def assertInside(self, node1, node2):
        inside = node1.mesh.contains(node2.mesh.vertices)
        if not inside.all():
            raise AssertionError(
                f"All vertices of {node2.name} should be inside {node1.name}")

    def assertClose(self, node1, node2, max_distance):
        closest_points = trimesh.proximity.closest_point(
            node1.mesh, node2.mesh.vertices)
        distances = closest_points[1]
        if not (distances <= max_distance).all():
            raise AssertionError(
                f"All points of {node2.name} should be at most "
                f"{max_distance} units away from {node1.name}")

    def assertFar(self, node1, node2, min_distance):
        closest_points = trimesh.proximity.closest_point(
            node1.mesh, node2.mesh.vertices)
        distances = closest_points[1]
        if not (distances >= min_distance).all():
            raise AssertionError(
                f"All points of {node2.name} should be at least "
                f"{min_distance} units away from {node1.name}")

    def assertIntersectVolumeAbove(self, node1, node2, min_volume):
        intersection = node1.mesh.intersection(node2.mesh)
        if intersection.volume < min_volume:
            raise AssertionError(
                f"The intersection volume of {node1.name} and {node2.name} "
                f"should be above {min_volume}")

    def assertIntersectVolumeBelow(self, node1, node2, max_volume):
        intersection = node1.mesh.intersection(node2.mesh)
        if intersection.volume > max_volume:
            raise AssertionError(
                f"The intersection volume of {node1.name} and {node2.name} "
                f"should be below {max_volume}")
