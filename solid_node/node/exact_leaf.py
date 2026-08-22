# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid2 import import_stl
from solid_node.exact import (cached_shape, shape_from_rendered, write_brep,
                              write_stl)
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

    def as_scad(self, rendered):
        """Export the model to STL and returns a scad code to render it.

        The export is skipped when the artifact on disk was already produced
        from these sources -- the same guard generate_stl() has always had,
        which this path used to run upstream of. A node that opts out of
        optimization still reaches here, so the guard belongs on the adapter
        and not only on the assemble() shortcut.
        """
        shape = shape_from_rendered(rendered)
        if not self._up_to_date(self.stl_file):
            write_stl(shape, self.stl_file, self.mtime_ns)
        if not self._up_to_date(self.brep_file):
            write_brep(shape, self.brep_file, self.mtime_ns)
        return import_stl(self.local_stl)
