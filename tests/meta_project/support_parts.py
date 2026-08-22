# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Parts for the gravity-support fixture projects.

Support is entirely a question of which solid sits above which, so every
part here is described by the world box it occupies once the fixture
places it: a corner-origin block, and the two interlocking shapes a
single block cannot express -- a hook that hangs by a lip reaching over
a post, and a pair of pieces whose lips reach over each other.
"""

from solid2 import cube

from solid_node.node import Solid2Node


class Block(Solid2Node):
    """A box of the given size, its lowest corner at the part origin."""

    def __init__(self, size=(2, 2, 2), name=None):
        self.size = list(size)
        super().__init__(size=list(size), name=name)

    def render(self):
        return cube(self.size)


class Hook(Solid2Node):
    """One printed part: a body hanging clear of a post, held only by a
    lip that reaches over the post's top face.

    Placed at the origin the lip spans x 0..2.5, z 1.2..1.7 and the body
    spans x 2.2..3.2, z -3..1.7, so the two overlap into one solid and
    the lip sits 0.2 above a post whose top face is at z = 1.
    """

    def render(self):
        return (cube([2.5, 2, 0.5]).translate([0, 0, 1.2])
                + cube([1, 2, 4.7]).translate([2.2, 0, -3]))


class LeftHook(Solid2Node):
    """The left half of a mutually leaning pair: a body with a lip
    reaching right, over the right hook's lip."""

    def render(self):
        return (cube([2, 2, 2]).translate([0, 0, 2])
                + cube([0.9, 2, 0.5]).translate([2, 0, 3.5]))


class RightHook(Solid2Node):
    """The right half: a lip under the left hook's lip, and an arm that
    reaches back over the left hook's body -- so each piece's drop lands
    in the other and neither grounds itself."""

    def render(self):
        return (cube([2, 2, 2]).translate([3, 0, 2])
                + cube([1.1, 2, 0.5]).translate([2.1, 0, 2])
                + cube([0.5, 2, 2]).translate([4, 0, 3])
                + cube([4.5, 2, 0.5]).translate([0, 0, 4.5]))
