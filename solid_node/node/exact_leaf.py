# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid2 import import_stl
from solid_node.exact import (cached_shape, deflections, shape_from_rendered,
                              write_brep, write_stl)
from solid_node.node.leaf import LeafNode


class ExactLeafNode(LeafNode):
    """Base for the leaf adapters whose backend is a B-rep kernel.

    Holds the exact-adapter contract that `exact-geometry` specifies and
    ADR-047 explains: because every exact backend converts its render result
    to one shared OCCT shape at the adapter boundary, everything after that
    conversion is one implementation rather than one per backend. A subclass
    supplies what genuinely differs -- its `namespace`, and whatever
    validation its own API needs.

    This is a framework-internal base, not a declared extension point: it
    lives here so that a correction to the contract lands once, not so that a
    project can subclass it.

    It deliberately declares no `namespace`, inheriting LeafNode's None, so
    it imposes none on a subclass.

    Kept out of leaf.py on purpose. That module imports nothing heavier than
    base, and putting this here would make every adapter that imports
    LeafNode -- Solid2Node included -- pull in exact.py and through it
    cadquery, trimesh and OCP.
    """

    #: The maximum distance, in millimetres, between this node's STL
    #: artifact and the surface it approximates -- OCCT's own
    #: `theLinDeflection`. Declared as a class attribute like
    #: `SheetLeafNode.thickness`: an edit lands in this node's own class
    #: body, which the source-set path already tracks (ADR-071), so it
    #: rebuilds this node's artifacts and nothing else. It is read and
    #: validated at export time, not here -- see `exact.deflections` --
    #: and never enters uniq_id (ADR-026/063): two tessellations of one
    #: solid are one node's artifact at two times, not two nodes.
    linear_deflection = 0.1

    #: The maximum angle, in radians, between the normals of two adjacent
    #: facets of this node's STL artifact -- OCCT's own
    #: `theAngDeflection`. Same declaration shape and same defaults as
    #: `linear_deflection` above.
    angular_deflection = 0.1

    @property
    def exact(self):
        return True

    def shape(self):
        if self._up_to_date(self.brep_file):
            return cached_shape(self.brep_file)
        if self.model is not None:
            return shape_from_rendered(self.model)
        rendered = self.render()
        self.validate(rendered)
        return shape_from_rendered(rendered)

    def materialize(self, rendered):
        """Export native BREP and STL artifacts.

        The export is skipped when the artifact on disk was already produced
        from these sources -- the same guard generate_stl() has always had,
        which this path used to run upstream of. A node that opts out of
        optimization still reaches here, so the guard belongs on the adapter
        and not only on the assemble() shortcut.

        The BREP is written before the STL, and not merely for symmetry
        with FusionNode.generate_stl(): `Shape.exportStl` calls
        `BRepMesh_IncrementalMesh`, which stores its triangulation ON the
        shape, and `Shape.exportBrep` serialises whatever triangulation the
        shape is carrying alongside its topology. Export the STL first and
        two builds of the same solid at different declared precision write
        BYTE-DIFFERENT `.brep` files, even though the topology --
        everything `shape()` and `.brep` promise -- never changed. Writing
        the BREP from the not-yet-meshed shape is what keeps it, and
        `shape()`, independent of whatever precision is declared.
        """
        shape = shape_from_rendered(rendered)
        digest = self.source_digest
        fingerprint = self.source_fingerprint
        if not self._up_to_date(self.brep_file):
            write_brep(shape, self.brep_file, self.mtime_ns, digest,
                       fingerprint)
        if not self._up_to_date(self.stl_file):
            linear_deflection, angular_deflection = deflections(self)
            write_stl(shape, self.stl_file, self.mtime_ns,
                      linear_deflection, angular_deflection, digest,
                      fingerprint)
    def as_scad(self, rendered):
        """Present the canonical native artifact to SCAD."""
        if not self._up_to_date(self.stl_file):
            self.materialize(rendered)
        return import_stl(self.local_stl)
