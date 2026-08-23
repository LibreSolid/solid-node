# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The mesh-import leaf: a committed STL file as a part.

Every other leaf authors its geometry in a CAD backend. Many worthwhile
designs are published only as meshes, so this one wraps a file the
project committed and makes it an ordinary part: it assembles, it fuses,
it exports, and it caches like any other leaf.

Three rules make that honest, and they are the whole of this module.

The mesh is admitted, not assumed. A file that is not a closed solid
fails at build time naming itself, unless the node declares
`require_watertight = False` -- because a mesh with holes has no
inside, and every consumer downstream (CGAL, slicers, volume
assertions) is entitled to one.

A file with several bodies is a plate of parts, not one part. A node
says which body it is by index, and a node that does not say raises an
error carrying the pack's whole inventory: the failure is the discovery
tool.

Corrections are code. Scale, framing and any other normalization belong
in an `adjust(self, mesh)` hook, which receives the selected mesh and
returns the corrected one -- no vocabulary of constructor knobs to
invent, and the correction is baked into the artifact so every consumer
sees one geometry.
"""

import os
import sys
import tempfile
import time

import trimesh
from solid2 import import_stl

from solid_node.node.leaf import LeafNode
from solid_node.node.sources import source_closure


#: Decimal places the body ordering compares centroids on. STL stores
#: coordinates as 32-bit floats, so two bodies laid out on the same
#: column of a print plate have x centroids that agree nominally and
#: differ in the last bits. Comparing the rounded value is what lets the
#: order actually fall through to y and then to z in that case, instead
#: of being decided by float noise. Three places is a micrometre: finer
#: than any real spacing between two parts on a plate, coarser than the
#: noise.
_CENTROID_PLACES = 3


def _load_source_mesh(path):
    """The committed file as one mesh.

    `force='mesh'` because a loader may hand back a Scene: what is
    wanted here is the geometry, and the bodies inside it are found by
    splitting, not by whatever grouping the file format happened to
    carry.
    """
    return trimesh.load(path, force='mesh')


def _centroid_key(body):
    return tuple(round(float(value), _CENTROID_PLACES)
                 for value in body.centroid)


def _bodies(mesh):
    """The mesh's connected components, ordered by centroid: x, then y,
    then z.

    `repair=False` is not an optimization. Left at its default, trimesh
    fills the holes of every component it splits out -- silently
    machining geometry the project did not author, and handing the
    watertight gate a repaired mesh to judge. The gate must see the
    file's real geometry.

    The order `split()` returns is library-internal, so it is never
    relied on: the components are always re-sorted before anything is
    indexed.
    """
    bodies = mesh.split(only_watertight=False, repair=False)
    if len(bodies) == 0:
        return [mesh]
    return sorted(bodies, key=_centroid_key)


def _open_edges(mesh):
    """Edges belonging to exactly one face: the holes in the surface."""
    return len(trimesh.grouping.group_rows(mesh.edges_sorted, require_count=1))


def _write_binary_stl(mesh, path, mtime_ns):
    """Write the artifact, stamped, in one atomic step.

    Temp-file-then-rename, and the stamp applied before the rename, so
    the file at `path` is never a half-written mesh and never carries a
    build-time mtime that would make it look newer than its source
    (following `solid_node.exact._atomic_export`).
    """
    directory = os.path.dirname(path) or '.'
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f'.{os.path.basename(path)}.', suffix='.tmp', dir=directory)
    os.close(descriptor)
    try:
        mesh.export(temporary, file_type='stl')
        os.utime(temporary, ns=(time.time_ns(), mtime_ns))
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


class StlNode(LeafNode):
    """A part that comes from a committed STL file.

    Declare the file with `stl_source`, as a path relative to the
    directory of the module defining the subclass::

        class Bracket(StlNode):

            stl_source = 'bracket.stl'

    Select one part out of a multi-body file with `body`, a 0-based
    index into the file's bodies ordered by centroid; a node that omits
    it on a multi-body file fails with the pack's inventory. Correct the
    mesh by implementing `adjust(self, mesh)`. Admit a mesh known not to
    be a closed solid with `require_watertight = False`.

    The node's geometry is its own artifact, materialized from the
    source file: the committed mesh is never imported in place, so
    fusion, piece identity, export and the viewer all see one thing.
    Producing it needs no external tool -- not even OpenSCAD, since the
    artifact is stamped with the source mtime exactly as `JScadNode`
    stamps the one `jscad` produced for it.
    """

    #: The committed mesh, relative to the wrapper module's directory.
    stl_source = None

    #: Which body of a multi-body file this part is, 0-based, indexing
    #: the bodies ordered by centroid (x, then y, then z). None means
    #: the file is expected to hold exactly one body.
    body = None

    #: Whether the selected mesh must be a closed solid to be admitted.
    #: Governs admission only: it never alters geometry, and it is not a
    #: constructor parameter, so it stays out of artifact identity.
    require_watertight = True

    #: An imported mesh belongs to no modelling library, so render()
    #: returns the node itself and there is no namespace to validate.
    namespace = None

    def __init__(self, *args, **kwargs):
        if not self.stl_source:
            raise ValueError(
                f'{self.__class__.__name__} is an StlNode and must declare '
                f'"stl_source", the path of an STL file in the same '
                f'directory as the python module defining it')

        module = sys.modules[self.__class__.__module__]
        wrapper = os.path.realpath(module.__file__)
        self.stl_source = os.path.realpath(
            os.path.join(os.path.dirname(module.__file__), self.stl_source))

        super().__init__(*args, **kwargs)

        # The wrapper module joins the tracked set, which no other
        # external-file leaf needs: a `.js` file is the whole of a
        # JScadNode's geometry, while an StlNode's `adjust` hook and
        # `body` index live in the python file and decide the part just
        # as much as the mesh does. The closure is transitive, so a
        # constant the hook imports is tracked too.
        self.files.update(source_closure(wrapper))

    def get_source_file(self):
        return self.stl_source

    def render(self):
        return self

    def as_scad(self, _):
        # The artifact is this node's own, always: there is no
        # import-the-file-in-place path. It is produced only when it is
        # stale, and the SCAD is the same either way.
        if not self._up_to_date(self.stl_file):
            _write_binary_stl(self._materialized_mesh(), self.stl_file,
                              self.mtime_ns)
        return import_stl(self.local_stl)

    ##############################################
    # Materialization

    def _materialized_mesh(self):
        """The geometry this node's artifact holds: the selected body,
        corrected by `adjust`, admitted by the gate."""
        mesh = self._selected_body(_load_source_mesh(self.stl_source))

        adjust = getattr(self, 'adjust', None)
        if adjust is not None:
            mesh = adjust(mesh)

        self._require_admissible(mesh)

        return mesh

    def _selected_body(self, mesh):
        """This node's body of the file, in the file's own coordinates.

        Extraction never reframes: the part stays where it sat in the
        pack, and bringing it to a usable frame is `adjust`'s job or a
        placement operation's.
        """
        bodies = _bodies(mesh)

        if self.body is None:
            if len(bodies) == 1:
                return bodies[0]
            raise ValueError(self._inventory(
                bodies,
                'holds more than one body, so it is a pack of parts and '
                'this node must say which one it is'))

        if not 0 <= self.body < len(bodies):
            raise ValueError(self._inventory(
                bodies, f'has no body {self.body}'))

        return bodies[self.body]

    def _inventory(self, bodies, complaint):
        """The pack, described. A developer or an agent learns what is
        in the file from the failure itself, so no separate inspection
        tool has to exist."""
        count = len(bodies)
        noun = 'body' if count == 1 else 'bodies'
        lines = '\n'.join(
            f'  body {index}: centroid {_point(body.centroid)}  '
            f'bounds {_point(body.bounds[0])}..{_point(body.bounds[1])}  '
            f'volume {float(body.volume):.3f}'
            for index, body in enumerate(bodies)
        )
        return (
            f'{self.name}: {self.stl_source} {complaint}. '
            f'It holds {count} {noun}; declare `body = <index>` to select '
            f'one, indexing this inventory:\n{lines}'
        )

    def _require_admissible(self, mesh):
        """The watertight gate.

        Judged here, on the final mesh, so a hook cannot smuggle a
        defect past it and a torn neighbour in a pack cannot condemn a
        sound part. The flag that opens the gate lives in the wrapper
        module, which this node tracks, so flipping it goes stale and
        re-runs the check on the next build.
        """
        if mesh.is_watertight or not self.require_watertight:
            return

        selected = '' if self.body is None else f' body {self.body}'
        raise ValueError(
            f'{self.name}: {self.stl_source}{selected} is not watertight -- '
            f'{_open_edges(mesh)} open edges leave the surface unclosed, so '
            f'the mesh encloses no solid. Repair the mesh, or declare '
            f'`require_watertight = False` on {self.__class__.__name__} to '
            f'admit it knowingly.')


def _point(values):
    return '(' + ', '.join(f'{float(value):.3f}' for value in values) + ')'
