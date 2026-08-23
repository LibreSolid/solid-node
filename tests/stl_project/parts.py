# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The project's imported parts, one class per part.

Every class here declares one mesh file and, where the mesh needs it,
the code that corrects or selects it. That code is the reason the
wrapper module joins the node's tracked source set: editing an `adjust`
hook or a `body` index changes the part just as an edit to the mesh
would.
"""

import numpy as np

from solid_node.node import StlNode

from .dimensions import MILLIMETRES_PER_INCH


class Bracket(StlNode):
    """The plain case: one body, no correction, taken as it sits."""

    stl_source = 'bracket.stl'


class SoleBodyBracket(StlNode):
    """The same single-body file, selecting the only body it has."""

    stl_source = 'bracket.stl'
    body = 0


class SecondBodyOfBracket(StlNode):
    """A body a single-body file does not have."""

    stl_source = 'bracket.stl'
    body = 1


class ScaledBracket(Bracket):
    """A mesh authored in inches, corrected in code rather than by a
    constructor knob -- and by a constant that lives in another module,
    which the node must therefore track too."""

    def adjust(self, mesh):
        return mesh.apply_scale(MILLIMETRES_PER_INCH)


class PunctureAdjustedBracket(Bracket):
    """A hook that breaks the mesh it was given. The gate runs after the
    hook precisely so this cannot reach an artifact."""

    def adjust(self, mesh):
        keep = np.ones(len(mesh.faces), dtype=bool)
        keep[0] = False
        mesh.update_faces(keep)
        return mesh


class UnselectedPack(StlNode):
    """A pack with no body declared: the error is the inventory."""

    stl_source = 'pack.stl'


class FirstPackPart(StlNode):
    stl_source = 'pack.stl'
    body = 0


class LastPackPart(StlNode):
    stl_source = 'pack.stl'
    body = 2


class OverflowPackPart(StlNode):
    stl_source = 'pack.stl'
    body = 7


class FirstTieBody(StlNode):
    """The tie pack orders on y and z, not on x alone."""

    stl_source = 'tie_pack.stl'
    body = 0


class SecondTieBody(StlNode):
    stl_source = 'tie_pack.stl'
    body = 1


class ThirdTieBody(StlNode):
    stl_source = 'tie_pack.stl'
    body = 2


class SoundNeighbour(StlNode):
    """The sound half of a pack whose other half is torn."""

    stl_source = 'mixed_pack.stl'
    body = 0


class TornNeighbour(StlNode):
    stl_source = 'mixed_pack.stl'
    body = 1


class LeakyPart(StlNode):
    stl_source = 'leaky.stl'


class AdmittedLeakyPart(StlNode):
    """The knowing escape hatch: this mesh is known to be open."""

    stl_source = 'leaky.stl'
    require_watertight = False
