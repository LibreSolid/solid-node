# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Exact B-rep geometry shared by nodes and geometric assertions."""

import os
import tempfile
import time

import cadquery as cq
import trimesh
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf
from OCP.TopTools import TopTools_ListOfShape

from solid_node import currency


_shape_cache = {}

# The cache key of every shape `_shape_cache` currently holds, by object
# address. An address is only a safe identity while something keeps the
# object alive, and `_shape_cache` is exactly that: an entry here is added
# and removed with the shape it names, so an address can never be reused
# behind a surviving entry.
#
# A shape cannot be its own key. `Shape.__eq__` is `isSame()`, which
# compares the underlying TShape and IGNORES location, so a shape and a
# differently placed copy of it compare equal -- keying placements on the
# shape would serve one part's placement for another's.
_shape_keys = {}

# One placed shape per (shape cache key, matrix), and one bounding box per
# shape cache key. `placed_shape` runs a full `BRepBuilderAPI_Transform`
# over the B-rep -- 6-19 ms on real parts -- and an animated assertion
# places the same solid by the same matrix at every candidate pair it
# visits.
_placement_cache = {}
_bounds_cache = {}


def _evict(brep_file):
    """Drop every cached artifact derived from a rebuilt file."""
    for key in [key for key in _shape_cache if key[0] == brep_file]:
        _shape_keys.pop(id(_shape_cache.pop(key)), None)
        _bounds_cache.pop(key, None)
        for placement in [placement for placement in _placement_cache
                          if placement[0] == key]:
            del _placement_cache[placement]


def cached_shape(brep_file):
    """Load one immutable CadQuery shape per ``(path, mtime)``."""
    mtime = os.path.getmtime(brep_file)
    key = (brep_file, mtime)
    cached = _shape_cache.get(key)
    if cached is None:
        _evict(brep_file)
        cached = cq.Shape.importBrep(brep_file)
        _shape_cache[key] = cached
        _shape_keys[id(cached)] = key
    return cached


def shape_identity(shape):
    """The cache key of a shape this module holds, or None.

    None means "no stable identity": a shape composed for this comparison
    or read from a node whose BREP is not current. A caller keying work on
    geometry must not cache such a shape's results.
    """
    return _shape_keys.get(id(shape))


def cached_bounding_box(shape):
    """The shape's local bounding box, computed once per cached shape.

    A shape with no cache identity -- one composed for this comparison, or
    read from a node whose BREP is not current -- is measured directly, as
    it is today.
    """
    key = _shape_keys.get(id(shape))
    if key is None:
        return shape.BoundingBox()
    bounds = _bounds_cache.get(key)
    if bounds is None:
        bounds = shape.BoundingBox()
        _bounds_cache[key] = bounds
    return bounds


def build123d_shape(rendered):
    """The OCCT shape of a build123d render result, or None if ``rendered``
    did not come from build123d.

    build123d and CadQuery are two front ends over one OCCT: every object of
    either wraps a single TopoDS_Shape, exposed as ``.wrapped``. Rewrapping
    that shape is therefore the whole conversion, and it is why a build123d
    node's exact geometry is carried as the CadQuery ``Shape`` the rest of
    this module trades in -- every consumer below (placement, fuse, common,
    BREP persistence, volume) then needs no backend special case, and a
    fusion may freely mix the two backends.

    build123d is recognised by module name rather than imported.
    ``solid_node.node`` imports every adapter eagerly and importing build123d
    costs about 1.6 seconds, which a project modelling in another backend
    should not pay.

    A builder is not itself geometry: ``with BuildPart() as part:`` is
    build123d's headline idiom, and returning the builder rather than its
    ``.part`` is the first mistake a user makes, so the finished part is
    taken. Returning None rather than raising leaves the diagnosis to
    Build123dNode.validate(), which can name the node.
    """
    if not type(rendered).__module__.startswith('build123d'):
        return None
    if not hasattr(rendered, 'wrapped'):
        rendered = getattr(rendered, 'part', None)
    if getattr(rendered, 'wrapped', None) is None:
        return None
    return cq.Shape.cast(rendered.wrapped)


def shape_from_rendered(rendered):
    """Return all shapes produced by a render as one shape."""
    from_build123d = build123d_shape(rendered)
    if from_build123d is not None:
        return from_build123d
    shapes = list(rendered.vals()) if hasattr(rendered, 'vals') else [rendered]
    if not shapes:
        raise ValueError('CadQuery render produced no shape')
    if len(shapes) == 1:
        return shapes[0]
    return cq.Compound.makeCompound(shapes)


def _atomic_export(path, mtime_ns, exporter, digest=None):
    """Write, stamp, and vouch for one exact artifact.

    `digest` is the node's source digest, recorded beside the artifact by
    `currency.publish` in the same step that puts it in place -- an
    artifact and the record of what produced it are written together or
    not at all. Defaulting to None means "no record", which costs a
    rebuild and never a stale answer, so a caller outside a node (an
    assertion helper, a test) is served correctly without one.
    """
    directory = os.path.dirname(path) or '.'
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f'.{os.path.basename(path)}.', suffix='.tmp', dir=directory)
    os.close(descriptor)
    try:
        exporter(temporary)
        os.utime(temporary, ns=(time.time_ns(), mtime_ns))
        currency.publish(temporary, path, digest)
    except Exception:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


def write_brep(shape, path, mtime_ns, digest=None):
    _atomic_export(path, mtime_ns, shape.exportBrep, digest)


def write_stl(shape, path, mtime_ns, digest=None):
    """Tessellate `shape` to an STL artifact without degenerate triangles.

    OCCT's mesher emits zero-area triangles on some vendor solids (shafts,
    standoffs, stepper frames); they add nothing to the surface and break
    the mesh engine's edge pairing, so every exact artifact -- a leaf's or
    a fused solid's -- drops them. The tessellation tolerances are the
    historical cq.exporters.export defaults.
    """
    def export(temporary):
        shape.exportStl(temporary, tolerance=0.1, angularTolerance=0.1)
        mesh = trimesh.load(temporary, file_type='stl', process=False)
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        mesh.export(temporary, file_type='stl')

    _atomic_export(path, mtime_ns, export, digest)


def _place(shape, values):
    transform = gp_Trsf()
    transform.SetValues(*values)
    return cq.Shape.cast(
        BRepBuilderAPI_Transform(shape.wrapped, transform, True).Shape())


def placed_shape(shape, matrix):
    """Place a local shape using the framework's composed 4x4 matrix.

    Cached per ``(shape cache key, matrix)``, so a solid placed by the same
    matrix twice is transformed once. The matrix is compared by its exact
    values: a placement difference too small to see is still a different
    placement, and this cache introduces no tolerance of its own. A shape
    with no cache identity is placed uncached, exactly as before.
    """
    values = tuple(float(matrix[row, column])
                   for row in range(3) for column in range(4))
    key = _shape_keys.get(id(shape))
    if key is None:
        return _place(shape, values)
    placement = (key, values)
    placed = _placement_cache.get(placement)
    if placed is None:
        placed = _place(shape, values)
        _placement_cache[placement] = placed
    return placed


def _boolean(operation, first, second, first_name, second_name):
    algorithm = {
        'intersection': BRepAlgoAPI_Common,
        'fusion': BRepAlgoAPI_Fuse,
    }[operation]()
    arguments = TopTools_ListOfShape()
    arguments.Append(first.wrapped)
    tools = TopTools_ListOfShape()
    tools.Append(second.wrapped)
    algorithm.SetArguments(arguments)
    algorithm.SetTools(tools)
    algorithm.SetRunParallel(True)
    try:
        algorithm.Build()
        if not algorithm.IsDone():
            raise RuntimeError('kernel reported not-done')
        return cq.Shape.cast(algorithm.Shape())
    except Exception as error:
        raise RuntimeError(
            f"Exact {operation} failed for {first_name} and "
            f"{second_name}: {error}"
        ) from error


def intersect_shapes(first, second, first_name, second_name):
    return _boolean('intersection', first, second, first_name, second_name)


def fuse_shapes(first, second, first_name, second_name):
    return _boolean('fusion', first, second, first_name, second_name)


def solid_count(shape):
    return len(shape.Solids())


def solid_volume(shape):
    return sum(solid.Volume() for solid in shape.Solids())
