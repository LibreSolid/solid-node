# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The flexible leaf backed by molejo.

molejo represents a swept flexible part analytically -- a closed profile
carried along a path, at a declared tessellation -- and evaluates that
representation to a mesh at a given binding. Two properties are what make
it usable as a node's geometry at frame rate: the document is the whole
truth (so it can travel into the viewer instead of a mesh per instant),
and the tessellation is declared rather than adaptive (so vertex count
and ordering are parameter-independent, and one binding's mesh
corresponds vertex for vertex with another's).

The adapter is deliberately thin. `FlexibleNode` next door owns the
mechanics every flexible technology shares; everything here is what is
specific to molejo: the `Shape` render contract, validated by the
established `namespace` mechanism exactly as every other adapter's
backend object is, and the evaluation itself. molejo's own failures --
an invalid spec, a parameter the binding does not bind -- are raised
verbatim: they already name the parameter and where in the document it is
referenced, which is better than anything a wrapper could say.
"""

import cadquery
import trimesh
from molejo.brep import evaluate as evaluate_brep

from solid_node.node.flexible import FlexibleNode


class MolejoNode(FlexibleNode):
    """A flexible part authored as a molejo shape.

    Declare one port per shape parameter and return the shape::

        class ValveSpring(MolejoNode):

            height = TranslationalPort(unit='mm')

            def render(self):
                return Shape(
                    profile=Circle(radius=2.0),
                    path=[Helix(radius=14.0, turns=6.5, height=P.height)],
                    path_samples=240, profile_samples=16,
                )

    `molejo.P.<name>` refers to the port of that name; the parent
    assembly binds it with `connect()`, and the two name sets have to
    agree exactly -- see `FlexibleNode`.
    """

    #: molejo's authoring classes live in modules under `molejo`, so the
    #: established namespace validation is the whole render check: a
    #: result from any other library is rejected naming this node.
    namespace = 'molejo'

    #: What the document tells a consumer to evaluate the spec with.
    tech = 'molejo'

    @property
    def exact(self):
        """molejo evaluates the same document to a B-rep solid, so this
        adapter is exact -- fixed by type, like every other adapter's,
        never by installation state or by which instant is bound. The
        OCCT kernel `molejo[brep]` needs is already a solid-node
        dependency through CadQuery, so nothing here is optional.
        """
        return True

    def _shape_parameters(self, rendered):
        return rendered.params

    def _shape_spec(self, rendered):
        return rendered.to_dict()

    def _snapshot_shape(self, rendered, values):
        # Cast to the CadQuery `Shape` the framework's exact geometry
        # trades in -- the same rewrapping of one TopoDS_Shape that
        # carries a build123d part across (see solid_node.exact) -- so
        # placement, Booleans and volume need no molejo special case and
        # a spring composes with a CadQuery part by the ordinary rule.
        result = evaluate_brep(self._shape_spec(rendered), values)
        return cadquery.Shape.cast(result.solid), result.tolerance

    def _snapshot_mesh(self, rendered, values):
        mesh = rendered.evaluate(**values)
        # process=False: molejo's vertices are the evaluation, and
        # merging or reordering them here would break the very
        # correspondence between bindings that its declared tessellation
        # exists to guarantee.
        return trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces,
                               process=False)

    def _snapshot_stl(self, rendered, values):
        return rendered.evaluate(**values).to_stl()
