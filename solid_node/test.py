# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import itertools
import math
import os
import re
import warnings
import numpy as np
import trimesh
from manifold3d import Manifold, Mesh
from unittest import TestCase as BaseTestCase

from solid_node.node.base import (cached_base_mesh, _compose_solid_matrix,
                                  _compose_world_matrix, _enclosing_solid,
                                  _topmost_rigid_nodes)
from solid_node.node.operations import Rotation, Translation


# Module-level cache of one manifold3d.Manifold per (stl_file, mtime)
# -- skill-repo docs/performance-improvement.md fix 3. Every
# trimesh.boolean.intersection call re-checks watertightness of BOTH
# meshes and re-converts both to Manifold, even when the caller only
# needs is_empty()/volume(); this cache pays that conversion (and the
# watertightness check) once per STL for the whole suite instead of
# once per boolean. Keyed the same way as cached_base_mesh (fix 1),
# with the same stale-entry eviction on rebuild.
_manifold_cache = {}


def _cached_manifold(stl_file):
    """(Manifold, local_bounds) for `stl_file`, built once per
    (stl_file, mtime) from the same trimesh mesh fix 1's
    cached_base_mesh loads (no extra disk read). Watertightness is
    validated ONCE here, at cache fill -- not on every boolean -- and
    raises a clear, STL-naming error if it fails, instead of letting
    an obscure failure surface deep inside the boolean engine."""
    mtime = os.path.getmtime(stl_file)
    key = (stl_file, mtime)
    cached = _manifold_cache.get(key)
    if cached is None:
        for stale_key in [k for k in _manifold_cache if k[0] == stl_file]:
            del _manifold_cache[stale_key]
        mesh = cached_base_mesh(stl_file)
        if not mesh.is_volume:
            raise ValueError(
                f"{stl_file} is not watertight -- cannot build a Manifold "
                "cache for spatial assertions")
        manifold = Manifold(mesh=Mesh(
            vert_properties=np.asarray(mesh.vertices, np.float32),
            tri_verts=np.asarray(mesh.faces, np.uint32),
        ))
        cached = (manifold, mesh.bounds.copy())
        _manifold_cache[key] = cached
    return cached


def _body_count(mesh):
    """Number of connected components in `mesh`.

    `only_watertight=False` is deliberate: the question is whether the
    geometry hangs together, and a fragment that is itself watertight
    is exactly the case worth catching -- filtering to watertight
    components would silently drop the evidence.
    """
    return len(mesh.split(only_watertight=False))


def _fast_geometry(node, compose_matrix=_compose_world_matrix):
    """(Manifold, local_bounds, world_matrix) for `node` if it exposes
    the attributes the fast path needs (docs/performance-improvement.md
    fixes 2+3) -- an .stl_file readable through the Manifold cache, so
    its cached Manifold and local .bounds come for free. Returns None
    for a node that only implements `.mesh` (e.g. the FakeNode test
    doubles in tests/test_assertions.py), which then falls back to a
    plain boolean over `.mesh` with no caching or culling."""
    stl_file = getattr(node, 'stl_file', None)
    if stl_file is None:
        return None
    manifold, bounds = _cached_manifold(stl_file)
    return manifold, bounds, compose_matrix(node)


def _world_bounds(local_bounds, matrix):
    """The conservative world AABB of a part: the axis-aligned box of
    its 8 local-bounds corners after the composed world matrix. A
    superset of the part's true world footprint -- exact for an
    axis-aligned, unrotated part, larger otherwise -- but cheap: 8
    points transformed instead of a full mesh."""
    lo, hi = local_bounds
    corners = np.array([[x, y, z, 1.0]
                        for x in (lo[0], hi[0])
                        for y in (lo[1], hi[1])
                        for z in (lo[2], hi[2])])
    world = (matrix @ corners.T).T[:, :3]
    return world.min(axis=0), world.max(axis=0)


def _boxes_disjoint(box1, box2):
    """True if two world AABBs (each a (min, max) pair) fail to
    overlap on some axis -- disjoint boxes make the exact intersection
    of the parts they bound exactly empty, whatever their real shapes
    are."""
    return bool(np.any(box1[1] < box2[0]) or np.any(box2[1] < box1[0]))


def _bounds_candidates(bounds):
    """Yield index pairs whose conservative world AABBs overlap.

    Sweep along X, retaining only intervals that can still reach the current
    box, then filter that active set on all three axes. The yielded set contains
    only genuine AABB overlaps and never materializes the N*(N-1)/2 pair set.
    As with every broad phase the dense worst case remains quadratic, but a
    sparse assembly keeps only its local neighborhood active.
    """
    order = sorted(range(len(bounds)),
                   key=lambda index: (bounds[index][0][0],
                                      bounds[index][1][0], index))
    active = []
    for current in order:
        current_min_x = bounds[current][0][0]
        active = [index for index in active
                  if bounds[index][1][0] >= current_min_x]
        for candidate in active:
            if _boxes_disjoint(bounds[candidate], bounds[current]):
                continue
            yield (min(candidate, current), max(candidate, current))
        active.append(current)


def _placed_assembly_solids(node):
    """Lazily world-placed Manifolds below ``node``.

    Each tuple is ``(solid, placed_manifold, world_bounds)``. The placement is
    Manifold's lazy ``transform()``: no conversion, no watertight re-check, and
    no evaluation until a candidate boolean actually reads the result.
    Selection is deliberately done before any geometry access so a rigid root
    can pass the public assertion without requiring its STL.
    """
    placed = []
    for solid in _topmost_rigid_nodes(node):
        manifold, local_bounds = _cached_manifold(solid.stl_file)
        matrix = _compose_world_matrix(solid)
        placed.append((
            solid,
            manifold.transform(matrix[:3, :4]),
            _world_bounds(local_bounds, matrix),
        ))
    return placed


def _candidate_intersection(solids, first, second):
    """Engine-native emptiness and volume for one placed solid pair."""
    result = solids[first][1] ^ solids[second][1]
    is_empty = result.is_empty()
    return is_empty, 0.0 if is_empty else result.volume()


def _intersection_stats(node1, node2, compose_matrix=_compose_world_matrix):
    """(is_empty, volume) for node1 ∩ node2 -- the shared helper the
    intersection-based assertions below route through. When BOTH
    nodes expose the fast-path attributes (see _fast_geometry):

    - An AABB broad-phase runs first (fix 2): if the parts' world
      boxes are disjoint, the exact intersection is provably empty
      and the boolean is skipped entirely (an exact-negative
      shortcut -- it never changes a verdict, only skips work).
    - Otherwise the cached Manifolds (fix 3) are placed with a lazy
      `.transform()` (cheap -- no conversion, no watertight re-check)
      and intersected directly (`a ^ b`); is_empty()/volume() are read
      off the result without ever converting it back to a trimesh.

    is_empty/volume mirror trimesh's own Trimesh.is_empty/.volume
    exactly: `is_empty` is Manifold's own is_empty() (empirically the
    same signal trimesh's `.is_empty` gave for the SAME geometry --
    verified directly against the real flush-contact fixtures in
    tests/meta_project/flush_strict.py and flush_keyed_strict.py,
    where a legitimate flush abutment reproducibly comes back
    non-empty with EXACTLY 0.0mm^3 volume; improvements.md #21's
    volume_epsilon contract depends on that non-empty verdict
    surviving at the strict volume_epsilon=0.0 default, so `volume`
    being 0 must NOT be folded into `is_empty` here -- only a
    volume_epsilon > 0 comparison (done by the callers below) may
    treat a 0-volume, non-empty result as free of real interference).
    `volume` is read only when the result is non-empty, exactly the
    `0.0 if intersection.is_empty else intersection.volume` shape the
    trimesh path already had.

    Falls back to the original trimesh.boolean.intersection over
    `.mesh` -- unchanged, no caching, no culling -- when either node
    lacks the fast-path attributes at all (e.g. the FakeNode test
    doubles in tests/test_assertions.py).
    """
    fast1 = _fast_geometry(node1, compose_matrix)
    fast2 = _fast_geometry(node2, compose_matrix)
    if fast1 is not None and fast2 is not None:
        manifold1, bounds1, matrix1 = fast1
        manifold2, bounds2, matrix2 = fast2
        box1 = _world_bounds(bounds1, matrix1)
        box2 = _world_bounds(bounds2, matrix2)
        if _boxes_disjoint(box1, box2):
            return True, 0.0
        placed1 = manifold1.transform(matrix1[:3, :4])
        placed2 = manifold2.transform(matrix2[:3, :4])
        result = placed1 ^ placed2
        is_empty = result.is_empty()
        volume = 0.0 if is_empty else result.volume()
        return is_empty, volume
    intersection = trimesh.boolean.intersection([node1.mesh, node2.mesh])
    volume = 0.0 if intersection.is_empty else intersection.volume
    return intersection.is_empty, volume


def _mesh_in_frame(node, compose_matrix):
    """Copy a node's base STL and place it in the requested frame.

    Mesh-only test doubles have no base artifact to reframe; their ``mesh`` is
    already treated as the caller's local geometry.
    """
    stl_file = getattr(node, 'stl_file', None)
    if stl_file is None:
        return node.mesh
    mesh = cached_base_mesh(stl_file).copy()
    mesh.apply_transform(compose_matrix(node))
    return mesh


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
        is_empty, volume = _intersection_stats(node1, node2)
        if not is_empty:
            raise AssertionError(
                f"{node1.name} should not intersect {node2.name} "
                f"(intersection volume {volume})"
            )

    def assertIntersecting(self, node1, node2):
        """Make sure node1 and node1 have some intersection"""
        is_empty, _ = _intersection_stats(node1, node2)
        if is_empty:
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
            is_empty, volume = _intersection_stats(node, against)
            is_fouling = (
                not is_empty if volume_epsilon <= 0
                else abs(volume) > volume_epsilon)
            if expect_intersect and not is_fouling:
                if is_empty:
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
    # Connectivity

    def assertNoDisconnectedSolids(self, node):
        """Assert every printed solid in ``node`` is one connected body.

        Each selected solid is read from its own STL with no placement
        operations composed. Connectivity is invariant under rigid placement,
        and rigid descendants are ingredients of the enclosing solid rather
        than independent parts.
        """
        for solid in _topmost_rigid_nodes(node):
            bodies = len(cached_base_mesh(solid.stl_file).split(
                only_watertight=False))
            if bodies != 1:
                raise AssertionError(
                    f"{solid.name} should be one connected body, but its STL "
                    f"contains {bodies} connected bodies")

    def assertNoSolidInterference(self, node):
        """Assert the printed solids below ``node`` share no volume.

        The topmost rigid nodes are placed in world coordinates at the testing
        instant already selected by the runner. Empty and zero-volume boundary
        contact pass; every positive candidate intersection reported by the
        kernel fails. There is intentionally no public overlap epsilon:
        manufacturing clearances are length-based project contracts, not a
        globally permitted volume of interpenetration.

        The spatial index is the sole verification path. Positive-volume
        interference is by definition material shared by SOME two solids, and
        any such pair has overlapping conservative world bounds -- so a
        complete broad phase reduces the assembly question to the pairs it
        emits. Triple overlap and full containment are covered by that same
        argument, not special-cased. Completeness is proved in
        tests/test_broad_phase_culling.py rather than re-checked here against
        a whole-assembly volume comparison: that comparison cost time
        proportional to the assembly's total triangle count on every passing
        run, could not name an offending pair, and only ever re-tested
        framework code that does not change between runs (ADR-040).
        """
        selected = list(_topmost_rigid_nodes(node))
        if len(selected) <= 1:
            return

        solids = _placed_assembly_solids(node)
        for first, second in _bounds_candidates(
                [item[2] for item in solids]):
            is_empty, volume = _candidate_intersection(
                solids, first, second)
            if is_empty or volume == 0.0:
                continue
            solid1 = solids[first][0]
            solid2 = solids[second][0]
            raise AssertionError(
                f"{solid1.name} should not interfere with {solid2.name} "
                f"(intersection volume {volume})")

    def assertJoined(self, node1, node2, min_weld_volume=0.0):
        """Assert node1 and node2 fuse into ONE connected body, i.e.
        that they are genuinely the same printed part.

        This is the one legitimate case in which two features must
        share volume, and it is the exact inverse of the adjacency
        rule that governs distinct parts. `min_weld_volume` (mm^3)
        additionally requires the shared volume welding them to be
        substantial rather than a numerical lick of contact.

        Both nodes must belong to the SAME solid. The comparison runs
        in that solid's frame, so two nodes from different solids would
        each be placed at their own part's origin -- discarding the
        distance the assembly holds between the parts, and reporting
        two features that share nothing as welded. Being asked whether
        two separate parts are one part is a question about the model,
        not the geometry, so it fails as such rather than being
        silently answered in the wrong frame.
        """
        solid1 = _enclosing_solid(node1)
        solid2 = _enclosing_solid(node2)
        if solid1 is not None and solid2 is not None and solid1 is not solid2:
            raise AssertionError(
                f"{node1.name} and {node2.name} cannot be joined: they "
                f"belong to different solids ({solid1.name} and "
                f"{solid2.name}). Features weld only inside one printed "
                f"part; parts placed by an assembly are separate by "
                f"construction"
            )
        _, weld_volume = _intersection_stats(
            node1, node2, compose_matrix=_compose_solid_matrix)
        union = trimesh.boolean.union([
            _mesh_in_frame(node1, _compose_solid_matrix),
            _mesh_in_frame(node2, _compose_solid_matrix),
        ])
        bodies = _body_count(union)
        if bodies != 1:
            raise AssertionError(
                f"{node1.name} and {node2.name} should be joined into one "
                f"body, but their union has {bodies} connected components "
                f"(shared volume {weld_volume})"
            )
        if min_weld_volume > 0 and abs(weld_volume) < min_weld_volume:
            raise AssertionError(
                f"{node1.name} and {node2.name} are joined by a weld of "
                f"only {weld_volume} mm^3, below the required "
                f"{min_weld_volume} mm^3"
            )

    ########################################
    # Adjacency sweep

    def assertNoPairwiseIntersections(self, node, volume_epsilon=0.0):
        """Deprecated compatibility assertion over every leaf pair.

        New whole-assembly tests should use ``assertNoSolidInterference``.
        This method retains its historical traversal and verdicts: walk the
        assembled tree rooted at `node` down to its leaves (a node with no
        children is a leaf; every other node's children are walked
        recursively) and assert that every pair is non-intersecting.

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
        warnings.warn(
            "assertNoPairwiseIntersections is deprecated; use "
            "assertNoSolidInterference, which checks topmost rigid solids "
            "without a public overlap epsilon",
            DeprecationWarning,
            stacklevel=2,
        )
        leaves = self._leaves(node)
        for leaf1, leaf2 in itertools.combinations(leaves, 2):
            is_empty, volume = _intersection_stats(leaf1, leaf2)
            if is_empty:
                continue
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
