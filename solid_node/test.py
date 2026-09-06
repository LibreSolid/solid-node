# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import itertools
import math
import os
import re
import warnings
from collections import namedtuple
from dataclasses import dataclass
import numpy as np
import trimesh
from scipy.optimize import linprog
from unittest import TestCase as BaseTestCase

from solid_node.mesh_engine import require_mesh_engine
from solid_node.node.base import (binding_hash, cached_base_mesh,
                                  _compose_solid_matrix,
                                  _compose_world_matrix, _enclosing_solid,
                                  _topmost_rigid_nodes)
from solid_node.node.operations import Rotation, Translation


def _deferred_exact(name):
    """Bind one `solid_node.exact` name without importing the kernel.

    Importing `solid_node.exact` imports cadquery, which costs about 1.5 s
    and pulls VTK in behind it. `solid_node.core.loader` already refuses to
    pay that for merely loading a node (see the `cli-startup-cost`
    capability); this is the same refusal one level in -- discovering or
    running tests must not pay it either, because a project modelling in
    solid2 and asserting over meshes never reaches the kernel at all.

    The deferral is a self-replacing callable rather than a module
    `__getattr__`: the names below are CALLED from this module's own
    functions, and a global-name lookup inside a function never consults a
    module's `__getattr__` -- it would raise NameError until something
    outside happened to read the attribute. A wrapper resolves on first
    call and rebinds the global, so every later call is the kernel function
    reached by an ordinary lookup, and the five call sites read exactly as
    they did.

    The rebinding declines to overwrite a global that is no longer this
    wrapper, so a caller that patched the name keeps its patch; and because
    the resolved name is a plain module global, a patch applied after
    resolution is equally honoured. An import failure surfaces here, at
    first use, naming what failed.
    """

    def deferred(*arguments, **keywords):
        from solid_node import exact
        resolved = getattr(exact, name)
        if globals().get(name) is deferred:
            globals()[name] = resolved
        return resolved(*arguments, **keywords)

    deferred.__name__ = name
    deferred.__qualname__ = name
    return deferred


cached_bounding_box = _deferred_exact('cached_bounding_box')
shape_identity = _deferred_exact('shape_identity')
fuse_shapes = _deferred_exact('fuse_shapes')
intersect_shapes = _deferred_exact('intersect_shapes')
placed_shape = _deferred_exact('placed_shape')
solid_count = _deferred_exact('solid_count')
solid_volume = _deferred_exact('solid_volume')


@dataclass(frozen=True)
class IntersectionStats:
    is_empty: bool
    volume: float
    exact: bool

    def __iter__(self):
        # Preserve the long-standing two-value private helper unpacking while
        # exposing which representation supplied the verdict.
        yield self.is_empty
        yield self.volume


########################################
# Comparison policy
#
# The kernel a run compares on is a property of the RUN, never of the
# model. A node's `exact` keeps reporting what its geometry can do; the
# policy says whether this run asks it to. Exact is the default and is
# today's run untouched. Faceted answers every geometric question on the
# parts' meshes -- the path a non-exact node already takes -- at
# tessellation precision, roughly 30x cheaper on a flexible part
# (spike/interference/FINDINGS.md, finding 6), and carries the one
# volume epsilon that exists only for it: meshes touch where solids
# only meet, and the epsilon is the developer's stated size for that.
#
# `solid test` resolves the policy from its flags and the environment
# and sets it before the first build; any other entry (a ScenarioTest
# under pytest, an assertion driven directly) resolves it from the
# environment at the first comparison. Resolved once per process: a run
# does not change kernel halfway.

ComparisonPolicy = namedtuple('ComparisonPolicy', 'kernel volume_epsilon')

KERNELS = ('exact', 'faceted')

_policy = None


def resolve_comparison_policy(kernel=None, volume_epsilon=None, environ=None):
    """The run's comparison policy from explicit values, then the
    environment, then the defaults.

    An explicit `kernel` (a flag) beats `SOLID_TEST_KERNEL`; an explicit
    `volume_epsilon` beats `SOLID_TEST_VOLUME_EPSILON`. The epsilon exists
    only for the faceted kernel: offered explicitly to the exact kernel it
    is refused, and the environment's value is not even read there, so a
    checkout's `.env` may carry both lines while CI overrides the kernel
    alone.
    """
    environ = os.environ if environ is None else environ
    if kernel is None:
        kernel = environ.get('SOLID_TEST_KERNEL') or 'exact'
        if kernel not in KERNELS:
            raise ValueError(
                f"SOLID_TEST_KERNEL must be 'exact' or 'faceted', not "
                f"{kernel!r}")
    elif kernel not in KERNELS:
        raise ValueError(f"unknown comparison kernel {kernel!r}")
    if kernel == 'exact':
        if volume_epsilon is not None:
            raise ValueError(
                'the exact kernel has nothing for a volume epsilon to '
                'absorb: drop --volume-epsilon or select --faceted')
        return ComparisonPolicy('exact', 0.0)
    if volume_epsilon is None:
        raw = environ.get('SOLID_TEST_VOLUME_EPSILON') or '0'
        try:
            volume_epsilon = float(raw)
        except ValueError:
            raise ValueError(
                f'SOLID_TEST_VOLUME_EPSILON must be a volume in mm³, not '
                f'{raw!r}') from None
    volume_epsilon = float(volume_epsilon)
    if volume_epsilon < 0:
        raise ValueError(
            f'the volume epsilon must not be negative ({volume_epsilon})')
    return ComparisonPolicy('faceted', volume_epsilon)


def set_comparison_policy(policy):
    """Fix the run's policy (the runner), or None to resolve again."""
    global _policy
    _policy = policy


def comparison_policy():
    """The run's policy, resolved from the environment on first use."""
    global _policy
    if _policy is None:
        _policy = resolve_comparison_policy()
    return _policy


def _routes_exact(node):
    """Whether this run compares `node` through its exact geometry."""
    return (comparison_policy().kernel == 'exact'
            and getattr(node, 'exact', False))


def _engine_reason(reason):
    """Why the mesh engine is needed: the caller's reason under the exact
    kernel, the run's choice under the faceted one."""
    if comparison_policy().kernel == 'faceted':
        return 'the run compares on the faceted kernel'
    return reason


def _settled(stats):
    """An engine verdict with the run's volume epsilon applied.

    Applied AFTER the verdict memo reads, so the cache holds raw verdicts
    and a policy change in one process never serves a filtered verdict as
    a raw one. At the default epsilon of 0.0 this changes nothing: the
    non-empty zero-volume flush contact of ADR-025/029 still fouls, and
    only a positive epsilon may call it clear.
    """
    epsilon = comparison_policy().volume_epsilon
    if epsilon > 0 and not stats.is_empty and abs(stats.volume) <= epsilon:
        return IntersectionStats(True, 0.0, stats.exact)
    return stats


# Module-level cache of one manifold3d.Manifold per (stl_file, mtime)
# -- skill-repo docs/performance-improvement.md fix 3. Every
# trimesh.boolean.intersection call re-checks watertightness of BOTH
# meshes and re-converts both to Manifold, even when the caller only
# needs is_empty()/volume(); this cache pays that conversion (and the
# engine's admissibility verdict) once per STL for the whole suite instead of
# once per boolean. Keyed the same way as cached_base_mesh (fix 1),
# with the same stale-entry eviction on rebuild.
_manifold_cache = {}

# Manifolds for flexible leaves, one per (uniq_id, binding). A flexible
# leaf has no artifact behind its inherited `stl_file` -- and a stale
# rigid artifact a predecessor of the node left at that path would
# answer with the wrong geometry -- so its Manifold is built from
# `base_mesh()`, the same evaluated-at-this-binding seam `mesh` and
# `_mesh_in_frame` already read. Keyed by the structural identity plus
# the binding hash: identical instances at one binding share a build,
# and rebinding evicts the stale entries the way a rebuilt STL does.
_flexible_manifold_cache = {}

# Companion cache holding only what the mesh engine is NOT needed for:
# a solid's local bounding box, a property of the STL read from the
# same cached base mesh, so it stays available -- and eager -- for
# every selected solid whether or not manifold3d is installed. It
# judges nothing: selecting a solid, placing it in the broad phase or
# comparing it on the exact kernel never asks whether its mesh is one
# the engine would accept. Only a faceted read asks, below.
_bounds_cache = {}


def _cached_local_bounds(stl_file):
    """Local bounds for `stl_file`, read once per (stl_file, mtime) from
    the same trimesh mesh fix 1's cached_base_mesh loads (no extra disk
    read).

    This half of the old combined cache deliberately needs no mesh
    engine: it is what lets the spatial index place an exact solid.
    """
    mtime = os.path.getmtime(stl_file)
    key = (stl_file, mtime)
    cached = _bounds_cache.get(key)
    if cached is None:
        for stale_key in [k for k in _bounds_cache if k[0] == stl_file]:
            del _bounds_cache[stale_key]
        cached = cached_base_mesh(stl_file).bounds.copy()
        _bounds_cache[key] = cached
    return cached


def _admitted(manifold, mesh, what):
    """`manifold` if the engine built it cleanly, else a ValueError
    naming `what` and the engine's own status.

    The engine judges its own input. trimesh's opinion of the mesh is
    reported beside it as a diagnostic -- it is what a human opens the
    file to look for -- but it decides nothing: OpenSCAD's four-face
    snap-tab edges and build123d's T-junctions are non-watertight to
    trimesh and NoError to Manifold, with the same volume, and a
    predicate stricter than the engine it guards refuses parts the
    engine would compare.
    """
    status = manifold.status()
    if status.name == 'NoError':
        return manifold
    raise ValueError(
        f"{what}: the mesh engine refuses this mesh ({status.name}) -- "
        f"cannot build a Manifold for spatial assertions; trimesh reads it "
        f"as {'watertight' if mesh.is_watertight else 'not watertight'}. "
        f"Repair or replace the mesh; nothing is repaired here")


_FACETED_NEEDED_BY = 'Comparing faceted geometry'
_FACETED_REASON = ('a part without exact geometry is compared through its '
                   'mesh')


def _cached_manifold(stl_file, needed_by=_FACETED_NEEDED_BY,
                     reason=_FACETED_REASON):
    """(Manifold, local_bounds) for `stl_file`, built once per
    (stl_file, mtime) from the same trimesh mesh fix 1's
    cached_base_mesh loads (no extra disk read).

    This is the ONE place a Manifold is constructed, and therefore the
    one place the mesh engine is required. It is reached only when a
    comparison actually reads faceted geometry -- never merely because
    a solid was selected -- so an assembly decided entirely by the
    boundary-representation kernel never calls it.
    """
    mtime = os.path.getmtime(stl_file)
    key = (stl_file, mtime)
    cached = _manifold_cache.get(key)
    if cached is None:
        Manifold, Mesh = require_mesh_engine(
            needed_by, _engine_reason(reason))
        for stale_key in [k for k in _manifold_cache if k[0] == stl_file]:
            del _manifold_cache[stale_key]
        bounds = _cached_local_bounds(stl_file)
        mesh = cached_base_mesh(stl_file)
        manifold = _admitted(Manifold(mesh=Mesh(
            vert_properties=np.asarray(mesh.vertices, np.float32),
            tri_verts=np.asarray(mesh.faces, np.uint32),
        )), mesh, stl_file)
        cached = (manifold, bounds)
        _manifold_cache[key] = cached
    return cached


def _flexible_manifold(node, needed_by=_FACETED_NEEDED_BY,
                       reason=_FACETED_REASON):
    """(Manifold, local_bounds) for a flexible leaf at its current
    binding, built from ``base_mesh()`` -- never from ``stl_file``,
    which for a flexible leaf names an artifact it does not write.
    """
    values = node.bound_values()
    key = (node.uniq_id, binding_hash(values))
    cached = _flexible_manifold_cache.get(key)
    if cached is None:
        Manifold, Mesh = require_mesh_engine(
            needed_by, _engine_reason(reason))
        for stale_key in [k for k in _flexible_manifold_cache
                          if k[0] == node.uniq_id]:
            del _flexible_manifold_cache[stale_key]
        mesh = node.base_mesh()
        bounds = (mesh.bounds[0].copy(), mesh.bounds[1].copy())
        manifold = _admitted(Manifold(mesh=Mesh(
            vert_properties=np.asarray(mesh.vertices, np.float32),
            tri_verts=np.asarray(mesh.faces, np.uint32),
        )), mesh, f"{node.name} at this binding")
        cached = (manifold, bounds)
        _flexible_manifold_cache[key] = cached
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
    if getattr(node, 'flexible', False):
        manifold, bounds = _flexible_manifold(node)
        return manifold, bounds, compose_matrix(node)
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
    box, then filter that active set on all three axes. The yielded set
    contains
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


class _DeferredManifold:
    """A solid's placed Manifold, built the first time something reads
    it and not before.

    Placement is what the spatial index needs; the Manifold is what a
    FACETED comparison needs. Separating them is the whole of the
    conditional mesh-engine contract: a pair the boundary-representation
    kernel decides never calls ``placed()``, so it never constructs a
    Manifold and never requires manifold3d. Construction still routes
    through ``_cached_manifold``, so the one-build-per-(stl_file, mtime)
    guarantee is unchanged however many placements share a file.
    """

    __slots__ = ('stl_file', 'matrix')

    def __init__(self, stl_file, matrix):
        self.stl_file = stl_file
        self.matrix = matrix

    def placed(self, needed_by, reason):
        """The lazily transformed Manifold, requiring the mesh engine."""
        manifold, _ = _cached_manifold(self.stl_file, needed_by, reason)
        return manifold.transform(self.matrix[:3, :4])


def _placed_manifold(record, needed_by, reason):
    """Read a placement record's Manifold, forcing a deferred one.

    The single funnel every faceted consumer goes through, so the
    virtual floor -- which is built as a real Manifold rather than
    deferred, having no STL behind it -- can share the same records.
    """
    manifold = record[1]
    if isinstance(manifold, _DeferredManifold):
        return manifold.placed(needed_by, reason)
    return manifold


def _solid_geometry(solid):
    """``(stl_file, local bounds, exact shape or None)`` for one
    selected solid: everything a placement needs that does not depend on
    WHERE the solid is being placed. Read once per solid so an assertion
    placing the same solid twice (see ``_dropped_assembly_solids``) pays
    for one ``shape()`` and one cache lookup, not two.

    Bounds come from the cached base mesh for EVERY solid, exact or
    faceted, so the conservative world boxes the broad phase, the
    grounded seeds and the virtual floor are all computed from -- and
    the candidate pairs they emit -- do not depend on whether a solid
    carries exact geometry.
    """
    local_bounds = _cached_local_bounds(solid.stl_file)
    shape = solid.shape() if _routes_exact(solid) else None
    return solid.stl_file, local_bounds, shape


def _place_solid(solid, stl_file, local_bounds, matrix, shape):
    """One placed-solid record: ``(solid, deferred_placed_manifold,
    world_bounds, placed_exact_shape_or_None, faceted_identity,
    exact_identity, matrix)``.

    The last three carry what the verdict memo needs and nothing reads
    otherwise: one identity per evaluation path, so a record is keyed by
    the geometry the path it takes actually compares, and the matrix the
    record was placed by, so a pair's RELATIVE placement can be formed
    without re-deriving it from the node tree.
    """
    return (solid, _DeferredManifold(stl_file, matrix),
            _world_bounds(local_bounds, matrix),
            None if shape is None else placed_shape(shape, matrix),
            _geometry_identity(stl_file),
            None if shape is None else shape_identity(shape),
            matrix)


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
        stl_file, local_bounds, shape = _solid_geometry(solid)
        placed.append(_place_solid(solid, stl_file, local_bounds,
                                   _compose_world_matrix(solid), shape))
    return placed


def _translation_matrix(offset):
    """The 4x4 world-frame translation by ``offset``."""
    matrix = np.eye(4)
    matrix[:3, 3] = offset
    return matrix


def _dropped_assembly_solids(solids, offset):
    """``(resting, dropped)`` placement records for ``solids``.

    Each solid is placed twice from ONE cache read: once by its composed
    world matrix, and once by that matrix with the drop translation applied
    outermost (``T @ M``), which is what makes the displacement a world-frame
    fall rather than a motion in the part's own frame. Both placements are the
    same lazy ``transform()`` the interference assertion uses, so the drop
    costs a matrix product, not a re-conversion.
    """
    translation = _translation_matrix(offset)
    resting, dropped = [], []
    for solid in solids:
        stl_file, local_bounds, shape = _solid_geometry(solid)
        matrix = _compose_world_matrix(solid)
        resting.append(
            _place_solid(solid, stl_file, local_bounds, matrix, shape))
        dropped.append(
            _place_solid(solid, stl_file, local_bounds,
                         translation @ matrix, shape))
    return resting, dropped


def _placed_intersection(first, second, needed_by=_FACETED_NEEDED_BY,
                         reason=_FACETED_REASON):
    """Engine-native emptiness and volume for two placed solid records,
    with the run's volume epsilon applied.

    A pair of exact records is read by the boundary-representation kernel;
    any other pair (faceted, or one of each) by the placed Manifolds.

    The exact branch returns before either record's Manifold is read, so
    it is also the branch that requires no mesh engine. Only the faceted
    branch below forces the deferred placements -- for BOTH records,
    including an exact one paired with a faceted partner, because that
    pair really is decided by the mesh boolean.
    """
    if first[3] is not None and second[3] is not None:

        def exact():
            result = intersect_shapes(
                first[3], second[3], first[0].name, second[0].name)
            count = solid_count(result)
            return IntersectionStats(count == 0, solid_volume(result), True)

        return _settled(
            _memoized(_record_key(first, second, 5, 'exact'), exact))

    def faceted():
        result = (_placed_manifold(first, needed_by, reason)
                  ^ _placed_manifold(second, needed_by, reason))
        is_empty = result.is_empty()
        return IntersectionStats(
            is_empty, 0.0 if is_empty else result.volume(), False)

    return _settled(
        _memoized(_record_key(first, second, 4, 'faceted'), faceted))


def _candidate_intersection(solids, first, second,
                            needed_by=_FACETED_NEEDED_BY,
                            reason=_FACETED_REASON):
    """Engine-native emptiness and volume for one placed solid pair."""
    return _placed_intersection(
        solids[first], solids[second], needed_by, reason)


########################################
# Support graph
#
# `assertAssemblySupported` asks a DIRECTED question about the same
# placed solids the interference assertion compares: does solid i,
# dropped along gravity, land inside solid j? The helpers below build
# that graph -- candidate pairs, seeds, declared edges, reachability --
# and are deliberately free of any physics beyond it (ADR-048).


def _unit_vector(vector, label):
    """``vector`` normalized, or a loud error for the zero vector -- a
    direction that cannot be normalized is a knob mistake, never a
    silently ignored argument."""
    values = np.asarray([float(component) for component in vector], float)
    magnitude = float(np.sqrt(np.dot(values, values)))
    if magnitude == 0:
        raise ValueError(
            f"assertAssemblySupported: {label} must be a nonzero vector")
    return values / magnitude


def _gravity_extent(bounds, unit_gravity):
    """How far a placed solid's conservative world box reaches ALONG
    gravity: the largest projection of the box on the gravity direction,
    which for an axis-aligned box is one per-axis maximum summed."""
    low, high = bounds
    return float(np.sum(np.maximum(unit_gravity * low, unit_gravity * high)))


def _support_candidates(dropped_bounds, placed_bounds):
    """Yield ``(supported, supporter)`` index pairs worth a Boolean.

    The broad phase is the same sweep-and-prune the interference assertion
    uses, run over both bound sets at once: dropped boxes first, placed boxes
    second, so an emitted pair spanning the two halves IS a directed
    displaced-versus-placed overlap. Pairs inside one half (two drops, or two
    resting solids) answer no question here and are dropped, as is a solid
    paired with its own drop.
    """
    count = len(dropped_bounds)
    boxes = list(dropped_bounds) + list(placed_bounds)
    for first, second in _bounds_candidates(boxes):
        if first < count <= second:
            supporter = second - count
            if supporter != first:
                yield first, supporter


def _selected_index(solids):
    """Identity map from selected solid to its index. Keyed by ``id``:
    a node is free to define ``__eq__``/``__hash__`` for its own
    purposes, and the question here is which OBJECT was selected."""
    return {id(solid): index for index, solid in enumerate(solids)}


def _resolve_selected(node, index_of):
    """The selected solids a caller's node stands for.

    A node inside a printed solid resolves UP to that solid -- the walk
    ``_enclosing_solid`` performs for ``assertJoined`` -- so naming a feature
    names its part. An assembly above the selection resolves DOWN to every
    selected solid beneath it, so naming a subassembly names its parts. A node
    that is neither resolves to nothing, which the callers report loudly
    rather than pass over.
    """
    current = node
    while current is not None:
        if id(current) in index_of:
            return [index_of[id(current)]]
        current = getattr(current, '_parent', None)
    return [index_of[id(solid)] for solid in _topmost_rigid_nodes(node)
            if id(solid) in index_of]


def _require_selected(node, index_of, role):
    resolved = _resolve_selected(node, index_of)
    if not resolved:
        raise ValueError(
            f"assertAssemblySupported: {role} "
            f"{getattr(node, 'name', node)!r} does not resolve to any "
            "selected topmost rigid solid")
    return resolved


def _declared_support_edges(supports, index_of):
    """``(supported, supporter)`` index edges for the declared holds."""
    edges = []
    for supported, supporter in supports:
        for first in _require_selected(supported, index_of, 'supports entry'):
            for second in _require_selected(
                    supporter, index_of, 'supports entry'):
                if first != second:
                    edges.append((first, second))
    return edges


def _grounded_seeds(solids, unit_gravity, max_drop, ground, index_of):
    """The indexes groundedness starts from.

    By default the assembly holds itself together: the solids reaching within
    ``max_drop`` of its furthest extent along gravity are the ones that would
    meet an unmodelled floor, and the drop distance doubles as the seed
    tolerance so seeding has the same resolution as the test. An explicit
    ``ground`` replaces that default outright.
    """
    if ground is None:
        extents = [_gravity_extent(item[2], unit_gravity) for item in solids]
        furthest = max(extents)
        return {index for index, extent in enumerate(extents)
                if furthest - extent <= max_drop}
    entries = ground if isinstance(ground, (list, tuple, set)) else [ground]
    seeds = set()
    for entry in entries:
        seeds.update(_require_selected(entry, index_of, 'ground'))
    return seeds


def _grounded_solids(edges, seeds):
    """Every index reachable from ``seeds`` against the support edges: if
    ``j`` is grounded and ``i`` rests on ``j``, ``i`` is grounded. A cycle of
    mutually leaning solids therefore grounds exactly when one of its members
    reaches a seed, and never by leaning on itself."""
    supporting = {}
    for supported, supporter in edges:
        supporting.setdefault(supporter, []).append(supported)
    grounded = set(seeds)
    queue = list(grounded)
    while queue:
        supporter = queue.pop()
        for supported in supporting.get(supporter, ()):
            if supported not in grounded:
                grounded.add(supported)
                queue.append(supported)
    return grounded


########################################
# Static equilibrium
#
# Reachability asks whether a solid has a path to ground. The helpers
# below ask the question that follows it: can push-only normal forces,
# over the interfaces those paths actually touch, balance every solid's
# weight AND the torque it makes about its own centre of mass. That is
# the classical rigid-body limit analysis, and it is decided for the
# whole assembly by one linear feasibility program (ADR-049).

# `assertAssemblySupported` is a REQUIRING path for any multi-solid
# assembly, exact solids included: contact extraction is always faceted
# (ADR-049 -- statics needs a patch's extent and direction, not Boolean
# validity) and the virtual floor is a meshed slab. There is no
# exact-only route to offer, so the assertion says so plainly rather
# than failing obscurely somewhere inside the equilibrium program.
_STATICS_NEEDED_BY = 'assertAssemblySupported'
_STATICS_REASON = (
    'proving frictionless static equilibrium extracts contact patches from '
    'meshed intersections for every body, exact solids included, and stands '
    'the assembly on a meshed virtual floor')

# A face whose normal is this close to perpendicular to gravity is a
# wall the displacement drove into, not a surface anything rests on.
_CONTACT_NORMAL_EPSILON = 1e-6

# Relative slack for classifying an intersection face to the boundary it
# came from. A face can lie on BOTH boundaries -- a solid dropped flush
# onto its seat produces exactly that -- and such a tie belongs to the
# supporter, so the comparison must not be decided by facet noise.
_CONTACT_SURFACE_EPSILON = 1e-6

# Relative slack a balance row may keep and still count as satisfied,
# scaled per body by its weight (force) and by weight times bounding-box
# diagonal (torque), so one tolerance reads the same at every size.
_BALANCE_TOLERANCE = 1e-5


class _VirtualFloor:
    """Stand-in for the unmodelled floor a default-grounded assembly
    stands on. It is never a selected solid and never answers a
    reachability question; it exists so the seeds have something real to
    push against."""

    name = 'the floor'


_FLOOR = _VirtualFloor()


@dataclass(frozen=True)
class _Body:
    """One rigid body as statics sees it: its placed faceted geometry,
    the weight and centre of mass of a uniform unit density under unit
    gravity, and whether the assembly's anchors already answer for its
    balance."""

    name: str
    manifold: object
    mesh: trimesh.Trimesh
    weight: float
    center: np.ndarray
    diagonal: float
    anchored: bool


@dataclass(frozen=True)
class _Contact:
    """One unilateral contact point. ``normal`` points out of
    ``supporter`` and toward ``supported``, so the only thing the
    interface can carry there is a push."""

    point: np.ndarray
    normal: np.ndarray
    supported: int
    supporter: int


def _placed_mesh(manifold):
    """The trimesh view of a placed Manifold: the facets the Boolean
    engine produced, already in world coordinates, ready for mass
    properties and nearest-surface queries."""
    mesh = manifold.to_mesh()
    return trimesh.Trimesh(
        vertices=np.asarray(mesh.vert_properties[:, :3], float),
        faces=np.asarray(mesh.tri_verts, np.int64),
        process=False)


def _statics_body(name, manifold, anchored):
    """One ``_Body`` from a placed Manifold.

    Mass properties are read off the placed facets at uniform unit
    density with unit gravity, so weight IS volume. Feasibility of the
    equilibrium program is invariant to positive scaling, which is why
    neither a density nor a gravitational constant ever has to be named.
    """
    mesh = _placed_mesh(manifold)
    low, high = mesh.bounds
    return _Body(name=name, manifold=manifold, mesh=mesh,
                 weight=float(abs(mesh.volume)),
                 center=np.asarray(mesh.center_mass, float),
                 diagonal=float(np.linalg.norm(high - low)),
                 anchored=anchored)


def _shrunk_patch(points, margin):
    """``points`` moved toward their own centroid by up to ``margin``.

    This is the whole of ``stability_margin``: the interior reserve a
    patch must keep for a balance resting on it to count. A point closer
    to the centroid than the margin collapses onto it.
    """
    if margin <= 0 or not len(points):
        return points
    centroid = points.mean(axis=0)
    offsets = points - centroid
    lengths = np.linalg.norm(offsets, axis=1, keepdims=True)
    scale = np.clip(1.0 - margin / np.maximum(lengths, 1e-12), 0.0, 1.0)
    return centroid + offsets * scale


def _interface_contacts(displaced, supported, supporter, offset,
                        unit_gravity, sense, margin):
    """Contact points and outward normals where ``supported``, displaced
    by ``offset``, enters ``supporter``.

    The displaced intersection is meshed and each of its faces is
    classified to the boundary it came from by nearest-surface distance.
    The supporter's faces are the interface: the supporter never moved,
    so those positions and normals lie on its real resting surface
    rather than on a displaced one. Contact extraction is always faceted,
    including for a pair of exact solids -- statics needs a patch's
    extent and direction, not Boolean validity, and support-edge
    existence keeps its own exact-kernel routing.

    ``sense`` is +1 for the drop sweep, which keeps the surfaces facing
    against gravity, and -1 for the lift sweep, which keeps the overhead
    restraints that complete a couple. A face whose normal is
    perpendicular to gravity is a wall the displacement merely drove
    into; it is dropped with the same conservatism that leaves friction
    out, and ``supports`` remains the visible escape for a hold that
    needs one.
    """
    intersection = displaced ^ supporter.manifold
    if intersection.is_empty():
        return []
    mesh = _placed_mesh(intersection)
    if not len(mesh.faces):
        return []
    normals = mesh.face_normals
    facing = sense * (normals @ unit_gravity) < -_CONTACT_NORMAL_EPSILON
    if not facing.any():
        return []
    centers = mesh.triangles_center[facing]
    to_supporter = supporter.mesh.nearest.on_surface(centers)[1]
    to_supported = supported.mesh.nearest.on_surface(centers - offset)[1]
    slack = _CONTACT_SURFACE_EPSILON * max(
        1.0, float(np.linalg.norm(mesh.extents)))
    landing = np.flatnonzero(facing)[to_supporter <= to_supported + slack]
    if not len(landing):
        return []
    found = {}
    for face, normal in zip(mesh.faces[landing], normals[landing]):
        for vertex in mesh.vertices[face]:
            found.setdefault(
                (tuple(np.round(vertex, 6)), tuple(np.round(normal, 6))),
                (vertex, normal))
    points = _shrunk_patch(
        np.array([point for point, _ in found.values()]), margin)
    return list(zip(points, [normal for _, normal in found.values()]))


def _gravity_frame(unit_gravity):
    """An orthonormal ``(lateral, lateral, up)`` basis whose third axis
    points straight out of gravity."""
    up = -unit_gravity
    helper = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(helper, up))) > 0.9:
        helper = np.array([0.0, 1.0, 0.0])
    first = np.cross(helper, up)
    first = first / np.linalg.norm(first)
    return first, np.cross(up, first), up


def _virtual_floor(solids, unit_gravity, max_drop):
    """The placement record of the floor a default-grounded assembly
    stands on: a slab built in the gravity frame, its top plane at the
    assembly's furthest extent along gravity and its footprint spanning
    the assembly laterally with room to spare.

    It joins the resting set for contact detection ONLY. Seeding keeps
    its ratified extent-based definition, and the floor never appears in
    the support graph -- what it changes is that a default-seeded solid
    must now balance on the patch it really lands on instead of being
    exempt for being lowest.
    """
    low = np.min([item[2][0] for item in solids], axis=0)
    high = np.max([item[2][1] for item in solids], axis=0)
    furthest = max(_gravity_extent(item[2], unit_gravity) for item in solids)
    first, second, up = _gravity_frame(unit_gravity)
    corners = np.array([[x, y, z]
                        for x in (low[0], high[0])
                        for y in (low[1], high[1])
                        for z in (low[2], high[2])])
    reach = float(np.linalg.norm(high - low)) + max_drop
    lateral = [corners @ first, corners @ second]
    size = np.array([float(axis.max() - axis.min()) + 2 * reach
                     for axis in lateral] + [reach])
    matrix = np.eye(4)
    matrix[:3, 0] = first
    matrix[:3, 1] = second
    matrix[:3, 2] = up
    matrix[:3, 3] = (first * float(lateral[0].mean())
                     + second * float(lateral[1].mean())
                     + up * (-furthest - size[2] / 2))
    Manifold, _ = require_mesh_engine(_STATICS_NEEDED_BY, _STATICS_REASON)
    manifold = Manifold.cube(list(size), True).transform(matrix[:3, :4])
    return (_FLOOR, manifold,
            _world_bounds((-size / 2, size / 2), matrix), None)


def _unbalanced_bodies(bodies, contacts, declared, unit_gravity):
    """Every body the equilibrium program cannot balance, each with the
    kind of balance that fails.

    One ``f_k >= 0`` per contact point carries ``f_k * n_k`` onto the
    supported body and its reaction onto a supporter that is not
    anchored. One free six-component wrench per declared ``supports``
    edge carries force and torque in both signs, which is what glue and
    a press fit really do. Six rows per non-anchored body state that the
    forces on it plus its weight vanish, and that their torque about its
    centre of mass vanishes.

    Elastic slack on every row makes the program always solvable, so ONE
    deterministic HiGHS solve yields both the verdict -- every row's
    slack inside its own tolerance -- and, when it fails, the bodies to
    name and whether force or torque is what they cannot close.
    """
    free = [index for index, body in enumerate(bodies) if not body.anchored]
    if not free:
        return []
    row_of = {index: 6 * position for position, index in enumerate(free)}
    rows = 6 * len(free)
    variables = len(contacts) + 6 * len(declared)
    matrix = np.zeros((rows, variables))
    target = np.zeros(rows)
    tolerance = np.zeros(rows)
    for position, index in enumerate(free):
        body = bodies[index]
        row = 6 * position
        target[row:row + 3] = -body.weight * unit_gravity
        scale = _BALANCE_TOLERANCE * max(body.weight, _BALANCE_TOLERANCE)
        tolerance[row:row + 3] = scale
        tolerance[row + 3:row + 6] = scale * max(body.diagonal, 1.0)
    for column, contact in enumerate(contacts):
        for index, sign in ((contact.supported, 1.0),
                            (contact.supporter, -1.0)):
            row = row_of.get(index)
            if row is None:
                continue
            force = sign * contact.normal
            matrix[row:row + 3, column] += force
            matrix[row + 3:row + 6, column] += np.cross(
                contact.point - bodies[index].center, force)
    for edge, (supported, supporter) in enumerate(declared):
        first = len(contacts) + 6 * edge
        for index, sign in ((supported, 1.0), (supporter, -1.0)):
            row = row_of.get(index)
            if row is None:
                continue
            center = bodies[index].center
            for axis in range(3):
                unit = np.zeros(3)
                unit[axis] = 1.0
                matrix[row:row + 3, first + axis] += sign * unit
                matrix[row + 3:row + 6, first + axis] += sign * np.cross(
                    -center, unit)
                matrix[row + 3:row + 6, first + 3 + axis] += sign * unit
    identity = np.eye(rows)
    solution = linprog(
        np.concatenate([np.zeros(variables), 1 / tolerance, 1 / tolerance]),
        A_eq=np.hstack([matrix, identity, -identity]), b_eq=target,
        bounds=([(0.0, None)] * len(contacts)
                + [(None, None)] * (6 * len(declared))
                + [(0.0, None)] * (2 * rows)),
        method='highs')
    if not solution.success:
        raise AssertionError(
            "assertAssemblySupported: the static equilibrium program did "
            f"not solve ({solution.message})")
    slack = np.abs(solution.x[variables:variables + rows]
                   - solution.x[variables + rows:])
    failures = []
    for position, index in enumerate(free):
        row = 6 * position
        kinds = [kind for kind, block in (('force', slice(row, row + 3)),
                                          ('torque', slice(row + 3, row + 6)))
                 if np.any(slack[block] > tolerance[block])]
        if kinds:
            failures.append((index, ' and '.join(kinds)))
    return failures


########################################
# Verdict memo
#
# A pair's intersection verdict depends on its two geometries and their
# RELATIVE rigid placement and on nothing else: emptiness and volume are
# invariant under a common rigid transform. So a repeated key is provably
# the same verdict, and the animation sweep repeats keys constantly --
# @testing_steps(N) recompares an assembly's static structure at every
# instant though none of it has moved relative to anything.
#
# Like the AABB broad phase this only ever skips work whose answer is
# already certain. It introduces NO tolerance: the relative matrix is
# compared by its exact bytes, so a placement difference too small to see
# is still a different placement. A near-miss costs a miss, which costs
# exactly what today costs.

# Bounded so a long-lived process (`solid develop`) cannot grow it without
# limit. A test run is far below this; the oldest entry goes first.
_VERDICT_CACHE_LIMIT = 8192

_verdict_cache = {}

# The mtime last seen for each geometry file, so a rebuild can drop the
# entries derived from the old content rather than leave them unreachable
# but resident -- the same eviction discipline the mesh, Manifold and
# placement caches follow.
_verdict_mtimes = {}


def _geometry_identity(path):
    """``(path, mtime)`` for a geometry file, or None if it has none."""
    if not path:
        return None
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    identity = (path, mtime)
    if _verdict_mtimes.get(path) != mtime:
        _verdict_mtimes[path] = mtime
        for key in [key for key in _verdict_cache
                    if key[0][0] == path or key[1][0] == path]:
            del _verdict_cache[key]
    return identity


def _verdict_key(identity1, matrix1, identity2, matrix2, path):
    """The identity under which a verdict stays valid, or None.

    None means "do not cache": one of the compared solids has no stable
    geometry identity, so nothing about a later comparison can be known to
    be the same question.
    """
    if identity1 is None or identity2 is None:
        return None
    relative = np.linalg.inv(matrix1) @ matrix2
    return (identity1, identity2, path, relative.tobytes())


def _record_key(first, second, identity_index, path):
    """The verdict key for a pair of placement records, or None.

    A record built outside ``_place_solid`` -- the virtual floor, which is
    a Manifold with no geometry file behind it -- carries no identity and
    is therefore never cached.
    """
    if len(first) <= 6 or len(second) <= 6:
        return None
    return _verdict_key(first[identity_index], first[6],
                        second[identity_index], second[6], path)


def _memoized(key, compute):
    """``compute()``, once per key."""
    if key is None:
        return compute()
    cached = _verdict_cache.get(key)
    if cached is None:
        cached = compute()
        if len(_verdict_cache) >= _VERDICT_CACHE_LIMIT:
            del _verdict_cache[next(iter(_verdict_cache))]
        _verdict_cache[key] = cached
    return cached


def _exact_verdict(shape1, matrix1, shape2, matrix2, name1, name2):
    """The exact path's verdict for one pair, broad phase included."""
    bounds1 = cached_bounding_box(shape1)
    bounds2 = cached_bounding_box(shape2)
    box1 = _world_bounds(
        (np.array([bounds1.xmin, bounds1.ymin, bounds1.zmin]),
         np.array([bounds1.xmax, bounds1.ymax, bounds1.zmax])), matrix1)
    box2 = _world_bounds(
        (np.array([bounds2.xmin, bounds2.ymin, bounds2.zmin]),
         np.array([bounds2.xmax, bounds2.ymax, bounds2.zmax])), matrix2)
    if _boxes_disjoint(box1, box2):
        return IntersectionStats(True, 0.0, True)
    result = intersect_shapes(
        placed_shape(shape1, matrix1), placed_shape(shape2, matrix2),
        name1, name2)
    count = solid_count(result)
    return IntersectionStats(count == 0, solid_volume(result), True)


def _faceted_verdict(manifold1, bounds1, matrix1,
                     manifold2, bounds2, matrix2):
    """The faceted path's verdict for one pair, broad phase included.

    Verdict semantics are untouched: ``is_empty`` is the engine's own
    emptiness, and ``volume`` is read only when non-empty, so a real flush
    abutment still comes back non-empty with exactly 0.0mm^3 and still
    fouls at the strict ``volume_epsilon=0`` default (ADR-025, ADR-029).
    """
    box1 = _world_bounds(bounds1, matrix1)
    box2 = _world_bounds(bounds2, matrix2)
    if _boxes_disjoint(box1, box2):
        return IntersectionStats(True, 0.0, False)
    placed1 = manifold1.transform(matrix1[:3, :4])
    placed2 = manifold2.transform(matrix2[:3, :4])
    result = placed1 ^ placed2
    is_empty = result.is_empty()
    volume = 0.0 if is_empty else result.volume()
    return IntersectionStats(is_empty, volume, False)


def _intersection_stats(node1, node2, compose_matrix=_compose_world_matrix):
    """(is_empty, volume) for node1 ∩ node2 -- the shared helper the
    intersection-based assertions below route through -- with the run's
    volume epsilon applied to the engine's verdict (see _settled).
    """
    return _settled(_engine_intersection_stats(node1, node2, compose_matrix))


def _engine_intersection_stats(node1, node2, compose_matrix):
    """The engine's own (is_empty, volume) for node1 ∩ node2. Two exact
    nodes take the exact path when the run's kernel is exact. When BOTH
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
    if _routes_exact(node1) and _routes_exact(node2):
        shape1 = node1.shape()
        shape2 = node2.shape()
        matrix1 = compose_matrix(node1)
        matrix2 = compose_matrix(node2)
        return _memoized(
            _verdict_key(shape_identity(shape1), matrix1,
                         shape_identity(shape2), matrix2, 'exact'),
            lambda: _exact_verdict(shape1, matrix1, shape2, matrix2,
                                   node1.name, node2.name))

    fast1 = _fast_geometry(node1, compose_matrix)
    fast2 = _fast_geometry(node2, compose_matrix)
    if fast1 is not None and fast2 is not None:
        manifold1, bounds1, matrix1 = fast1
        manifold2, bounds2, matrix2 = fast2
        return _memoized(
            _verdict_key(_geometry_identity(getattr(node1, 'stl_file', None)),
                         matrix1,
                         _geometry_identity(getattr(node2, 'stl_file', None)),
                         matrix2, 'faceted'),
            lambda: _faceted_verdict(manifold1, bounds1, matrix1,
                                     manifold2, bounds2, matrix2))
    intersection = trimesh.boolean.intersection([node1.mesh, node2.mesh])
    volume = 0.0 if intersection.is_empty else intersection.volume
    return IntersectionStats(intersection.is_empty, volume, False)


def _mesh_in_frame(node, compose_matrix):
    """Copy a node's base geometry and place it in the requested frame.

    Through ``base_mesh`` rather than the STL directly, so a node kind whose
    geometry is not a cached artifact -- a flexible leaf, which evaluates its
    current binding -- is reframed here exactly as ``node.mesh`` reframes it
    in world coordinates.

    Mesh-only test doubles have no base geometry to reframe; their ``mesh`` is
    already treated as the caller's local geometry.
    """
    base_mesh = getattr(node, 'base_mesh', None)
    if base_mesh is None:
        return node.mesh
    mesh = base_mesh()
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
        """Require node1-to-node2 distance to be below max_distance."""
        closest_points = trimesh.proximity.closest_point(
            node1.mesh, node2.mesh.vertices)
        distances = closest_points[1]
        if not (distances <= max_distance).all():
            raise AssertionError(
                f"All points of {node2.name} should be at most "
                f"{max_distance} units away from {node1.name}")

    def assertFar(self, node1, node2, min_distance):
        """Require node1-to-node2 distance to be above min_distance."""
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
        _, volume = _intersection_stats(node1, node2)
        if volume < min_volume:
            raise AssertionError(
                f"The intersection volume of {node1.name} and {node2.name} "
                f"should be above {min_volume}")

    def assertIntersectVolumeBelow(self, node1, node2, max_volume):
        """Make sure the volume of the intersection between node1 and node2
        is lesser than max_volume.
        """
        _, volume = _intersection_stats(node1, node2)
        if volume > max_volume:
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
    # inserted into node.operations before every pre-existing
    # operation, at index 0 (ADR-025 as amended by ADR-075).
    #
    # That single insertion rule is what makes both modes "local":
    # a rotation turns node about its OWN axis rather than the world
    # origin, because it runs before node has been moved away from
    # the origin by any of its own operations; a translation likewise
    # moves node along `along` in node's own untransformed frame --
    # so every Rotation of node's own, a leading one included, and
    # every one of an ancestor assembly's, applies to the mesh AFTER
    # the perturbation and carries its direction along with it.
    # `along` is a direction in node's own frame, not a fixed world
    # vector and not the parent's -- that carrying is the point.
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
        paths = []
        for signed_value in self._signed_perturbations(angle, directions):
            paths.append(self._assert_perturbation(
                node, signed_value, against, axis, along, unit_along,
                expect_intersect=True, volume_epsilon=volume_epsilon))
        self._warn_ignored_epsilon(
            'assertBlockedBeyond', volume_epsilon, paths)

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
        paths = []
        for one_angle in angles:
            for signed_value in self._signed_perturbations(
                    one_angle, directions):
                paths.append(self._assert_perturbation(
                    node, signed_value, against, axis, along, unit_along,
                    expect_intersect=False, volume_epsilon=volume_epsilon))
        self._warn_ignored_epsilon('assertFreeWithin', volume_epsilon, paths)

    def _warn_ignored_epsilon(self, assertion, volume_epsilon, paths):
        if volume_epsilon > 0 and paths and all(paths):
            warnings.warn(
                f'{assertion} ignored volume_epsilon={volume_epsilon} '
                'because every comparison used exact geometry',
                UserWarning,
                stacklevel=3,
            )

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
        # Before every pre-existing operation, whatever comes first:
        # the node's own frame is the frame, always (ADR-075).
        node.operations.insert(0, operation)
        try:
            stats = _intersection_stats(node, against)
            is_empty, volume = stats
            is_fouling = (
                not is_empty if stats.exact or volume_epsilon <= 0
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
            return stats.exact
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
            if _routes_exact(solid):
                bodies = solid_count(solid.shape())
                source = 'exact geometry'
            else:
                bodies = len(cached_base_mesh(solid.stl_file).split(
                    only_watertight=False))
                source = 'STL'
            if bodies != 1:
                raise AssertionError(
                    f"{solid.name} should be one connected body, but its "
                    f"{source} "
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
                solids, first, second, 'assertNoSolidInterference',
                'one of the two solids in a candidate pair has no exact '
                'geometry, so the pair is compared through their meshes')
            if is_empty or volume == 0.0:
                continue
            solid1 = solids[first][0]
            solid2 = solids[second][0]
            raise AssertionError(
                f"{solid1.name} should not interfere with {solid2.name} "
                f"(intersection volume {volume})")

    def assertAssemblySupported(self, node, gravity=(0, 0, -1), max_drop=1.0,
                                ground=None, supports=None,
                                stability_margin=0.0):
        """Assert every printed solid below ``node`` is held against gravity.

        The same topmost rigid solids ``assertNoSolidInterference`` compares
        are placed in world coordinates at the testing instant already
        selected by the runner. A solid is DIRECTLY supported by another when,
        displaced by ``max_drop`` along the normalized ``gravity`` vector, it
        intersects that solid with positive volume: a part resting on a face,
        sitting in its clearance gap, or hanging by an engaged lip all land in
        their support, while a part floating in space lands in nothing.
        Zero-volume boundary contact after the drop is not a hold, exactly as
        it is not interference. Those relations form a support graph, and
        every selected solid must reach a grounded solid through it; the
        failure names every solid that does not.

        Reaching ground is not standing up, so a second phase then proves
        FRICTIONLESS STATIC EQUILIBRIUM: that some distribution of push-only
        normal forces over the detected contact interfaces balances every
        non-anchored solid's weight and the torque it makes about its own
        centre of mass, all of them at once. Interfaces come from the same
        displaced intersections, on the supporter's real undisplaced surface,
        in both directions -- the drop, and a lift against gravity that finds
        the overhead restraints completing a couple (a cantilevered pin in a
        snug hole balances on its hole's lower and upper walls). Lift
        contacts never add support-graph edges. The failure names every solid
        that cannot be balanced and whether its force or its torque is what
        does not close.

        With ``ground=None`` the assembly must hold itself together: the
        solids reaching within ``max_drop`` of the assembly's furthest extent
        along gravity are grounded, which is also what an unmodelled floor
        would touch, and for the equilibrium phase that floor is the only
        anchored body -- a top-heavy solid standing on too small a foot fails
        instead of being exempt for being lowest. ``ground`` (a node or a
        sequence of nodes, each resolved to its selected solid) replaces that
        default for an assembly anchored somewhere else -- hung from a
        ceiling, bolted to an unmodelled frame: those solids are then the only
        seeds and the only anchored bodies, and no floor exists.

        ``supports=[(supported, supporter), ...]`` declares holds this
        assertion deliberately cannot prove -- press fits, glue, friction --
        keeping the exemption visible in the test. A declared edge grounds the
        supported solid and transmits an unrestricted wrench between the pair,
        force and torque in both signs. A declared supporter must still be
        grounded itself; declaring an edge grounds nothing by itself. A
        ``ground`` or ``supports`` entry resolving to no selected solid, a
        zero ``gravity`` vector, a non-positive ``max_drop`` and a negative
        ``stability_margin`` are errors.

        ``stability_margin`` (mm, default 0.0) shrinks every contact patch
        toward its own centroid before the equilibrium decision. At the
        default the check is pure feasibility, so a knife-edge balance with
        the centre of mass exactly over a patch boundary passes; a positive
        margin demands that much interior reserve and rejects it.

        Choosing ``max_drop`` (mm, default 1.0): it must be LARGER than the
        design's vertical clearance play, or a part sitting in its own
        clearance gap reads as floating, and SMALLER than the thinnest
        supporting feature's thickness plus the gap above it, or the dropped
        solid tunnels straight through its support and the same part reads as
        floating again. The default sits in the usual window between printed
        clearances (0.5mm or less) and printed walls (1.2mm or more). The same
        window bounds the contact patches: a drop that tunnels past a
        supporting face cannot extract the interface resting on it.

        What this assertion claims: support reachability, force balance,
        torque balance and toppling over the contacts it detects. What it does
        NOT claim: friction, adhesion, purely lateral (gravity-parallel) wall
        reactions, the toppling of a single solid on the floor (a lone solid
        still passes without geometric work), and every dynamic effect. A hold
        that is real but outside frictionless statics belongs in ``supports``.
        """
        unit_gravity = _unit_vector(gravity, 'gravity')
        max_drop = float(max_drop)
        if not max_drop > 0:
            raise ValueError(
                "assertAssemblySupported: max_drop must be positive, "
                f"got {max_drop}")
        stability_margin = float(stability_margin)
        if stability_margin < 0:
            raise ValueError(
                "assertAssemblySupported: stability_margin must not be "
                f"negative, got {stability_margin}")

        selected = list(_topmost_rigid_nodes(node))
        if len(selected) <= 1:
            # Nothing can rest on anything: the selection is already a
            # supported assembly, and no geometry is loaded to say so.
            return

        # A requiring path in full: fail here, naming the assertion and
        # the reason, rather than partway through the support graph.
        require_mesh_engine(_STATICS_NEEDED_BY, _STATICS_REASON)

        index_of = _selected_index(selected)
        declared = _declared_support_edges(supports or (), index_of)

        offset = unit_gravity * max_drop
        resting, dropped = _dropped_assembly_solids(selected, offset)
        seeds = _grounded_seeds(
            resting, unit_gravity, max_drop, ground, index_of)
        # The floor is a landing target, never a support edge: it holds
        # the seeds up in the equilibrium phase and answers no
        # reachability question at all.
        targets = list(resting)
        if ground is None:
            targets.append(_virtual_floor(resting, unit_gravity, max_drop))

        edges = []
        landings = []
        for supported, supporter in _support_candidates(
                [item[2] for item in dropped], [item[2] for item in targets]):
            is_empty, volume = _placed_intersection(
                dropped[supported], targets[supporter],
                _STATICS_NEEDED_BY, _STATICS_REASON)
            if is_empty or volume == 0.0:
                continue
            landings.append((supported, supporter))
            if supporter < len(selected):
                edges.append((supported, supporter))
        edges.extend(declared)

        grounded = _grounded_solids(edges, seeds)
        unsupported = [solid for index, solid in enumerate(selected)
                       if index not in grounded]
        if unsupported:
            names = ', '.join(solid.name for solid in unsupported)
            direction = ', '.join(f'{value:g}' for value in unit_gravity)
            raise AssertionError(
                f"{names} should be supported against gravity, but no "
                f"support path reaches a grounded solid "
                f"(dropped {max_drop:g}mm along gravity ({direction}))")

        self._assert_static_equilibrium(
            selected, targets, dropped, landings, declared,
            set() if ground is None else seeds,
            unit_gravity, offset, stability_margin)

    def _assert_static_equilibrium(self, selected, targets, dropped, landings,
                                   declared, anchors, unit_gravity, offset,
                                   margin):
        """The second phase of ``assertAssemblySupported``: prove the
        reachable assembly can also stand.

        Contacts are extracted from every landing the drop found and from
        every candidate of a symmetric lift sweep, which is what makes an
        engaged couple balance legitimately instead of demanding an
        exemption. A body whose support edges yield no extractable
        interface keeps its six unsatisfiable rows and fails here, rather
        than passing for having had a path.
        """
        def body_manifold(record):
            return _placed_manifold(
                record, _STATICS_NEEDED_BY, _STATICS_REASON)

        bodies = [_statics_body(record[0].name, body_manifold(record),
                                index in anchors)
                  for index, record in enumerate(targets[:len(selected)])]
        bodies.extend(_statics_body(record[0].name, body_manifold(record),
                                    True)
                      for record in targets[len(selected):])

        contacts = []
        for supported, supporter in landings:
            contacts.extend(
                _Contact(point, normal, supported, supporter)
                for point, normal in _interface_contacts(
                    body_manifold(dropped[supported]), bodies[supported],
                    bodies[supporter], offset, unit_gravity, 1.0, margin))
        lifted = _dropped_assembly_solids(selected, -offset)[1]
        for supported, supporter in _support_candidates(
                [item[2] for item in lifted],
                [item[2] for item in targets]):
            contacts.extend(
                _Contact(point, normal, supported, supporter)
                for point, normal in _interface_contacts(
                    body_manifold(lifted[supported]), bodies[supported],
                    bodies[supporter], -offset, unit_gravity, -1.0, margin))

        failures = _unbalanced_bodies(bodies, contacts, declared, unit_gravity)
        if failures:
            reasons = '; '.join(
                f"{bodies[index].name} cannot rest in frictionless static "
                f"equilibrium on its detected contacts (unbalanced {kind})"
                for index, kind in failures)
            raise AssertionError(
                f"{reasons}. Declare a hold that is real but outside "
                f"frictionless statics in supports=[(supported, supporter)]")

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
        if _routes_exact(node1) and _routes_exact(node2):
            shape1 = placed_shape(
                node1.shape(), _compose_solid_matrix(node1))
            shape2 = placed_shape(
                node2.shape(), _compose_solid_matrix(node2))
            union = fuse_shapes(shape1, shape2, node1.name, node2.name)
            bodies = solid_count(union)
        else:
            union = trimesh.boolean.union([
                _mesh_in_frame(node1, _compose_solid_matrix),
                _mesh_in_frame(node2, _compose_solid_matrix),
            ])
            bodies = _body_count(union)
        if weld_volume == 0.0:
            bodies = max(bodies, 2)
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
        paths = []
        for leaf1, leaf2 in itertools.combinations(leaves, 2):
            stats = _intersection_stats(leaf1, leaf2)
            paths.append(stats.exact)
            is_empty, volume = stats
            if is_empty:
                continue
            if (not stats.exact and volume_epsilon > 0
                    and abs(volume) <= volume_epsilon):
                continue
            message = (
                f"{leaf1.name} should not intersect {leaf2.name} "
                f"(intersection volume {volume})")
            if volume_epsilon > 0:
                message += f", exceeds epsilon {volume_epsilon}"
            raise AssertionError(message)
        self._warn_ignored_epsilon(
            'assertNoPairwiseIntersections', volume_epsilon, paths)

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
    of the animation that should be used to run the test.

    The instant is handed to `set_keyframe` unchanged, so it means what
    the tested root's time base says: a fraction of the 0..1 timeline
    for a root declaring none, seconds for a root declaring
    `time = Time(loop=...)`.
    """
    def decorator(method):
        method.testing_instants = [instant]
        return method

    return decorator


def testing_steps(steps, start=0, end=1):
    """Use this decorator to run the test in several steps
    of the animation. Use start and end to define the range
    in that will be divided in those steps.

    Instants are handed to `set_keyframe` unchanged: fractions of the
    0..1 timeline for a root declaring no time base, seconds for a root
    declaring `time = Time(loop=...)` -- so a sweep over such a root
    states the span it covers in seconds (`end=1.5` for one beat of a
    1.5 s pendulum); the defaults do not follow the declaration.
    """
    if steps < 2:
        raise AssertionError("Expected at least 2 steps, "
                             "for single step use @testing_instant instead"
                             )

    duration = end - start
    step = duration / (steps - 1)
    instants = [start + i * step for i in range(steps)]
    instants[-1] = end

    def decorator(method):
        method.testing_instants = instants
        return method

    return decorator
