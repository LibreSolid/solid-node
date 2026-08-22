# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Parts for the gravity-support fixture projects.

Support is a question of which solid sits above which, and standing up
is a question of where each solid's mass sits over the patches it
lands on -- so every part here is described by the world box it
occupies once the fixture places it, plus, where it matters, where that
puts its centre of mass.
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


class TopHeavy(Solid2Node):
    """One printed part standing on a foot far too small for it: a
    2-wide foot under a head reaching out to x = 8, so its centre of
    mass at x = 3.4 falls well outside the footprint it lands on."""

    def render(self):
        return cube([2, 2, 2]) + cube([8, 2, 2]).translate([0, 0, 2])


class BoredBlock(Solid2Node):
    """A grounded block with a snug horizontal hole through it: the
    hole's lower wall sits at z = 2.9 and its upper wall at z = 4.1,
    0.1 of clearance around a pin 1 thick."""

    def render(self):
        return (cube([4, 6, 6])
                - cube([5, 2.2, 1.2]).translate([-0.5, 1.9, 2.9]))


class Pin(Solid2Node):
    """The pin that hole carries: engaged over x 0..4 and cantilevered
    out to x = 14, so only a couple between the hole's two walls can
    balance it."""

    def render(self):
        return cube([14, 2, 1]).translate([0, 2, 3])


class Hook(Solid2Node):
    """One printed part: a body hanging clear of a post, held only by a
    lip that reaches over the post's top face.

    Placed at the origin the lip spans x -3..2.5, z 1.2..2.2 and the body
    spans x 2.2..3.2, z -3..2.2. The lip is 1.0 thick over a 0.2 gap, so
    a 1.0 drop still straddles the post's top face at z = 1 instead of
    tunnelling past it, and the lip's reach to the left of the post puts
    the hook's centre of mass at x = 1.15 -- over the post's top face,
    which is the only patch holding it.
    """

    def render(self):
        return (cube([5.5, 2, 1]).translate([-3, 0, 1.2])
                + cube([1, 2, 5.2]).translate([2.2, 0, -3]))


class LeftHook(Solid2Node):
    """The left half of a mutually leaning pair: the heavy piece that
    stands on the slab, with a shelf reaching right under the right
    hook's tongue and a tongue reaching right over the right hook's
    shelf."""

    def render(self):
        return (cube([4, 2, 14]).translate([0, 0, 2])          # body
                + cube([3, 2, 2]).translate([3.5, 0, 2])       # shelf
                + cube([2, 2, 2]).translate([3.5, 0, 7.5]))    # tongue


class RightHook(Solid2Node):
    """The right half: its tongue rests on the left hook's shelf and its
    shelf carries the left hook's tongue, so each piece's drop lands in
    the other and neither grounds itself. Its centre of mass at x = 7.21
    lies outside the patch that holds it up, which is exactly what the
    left tongue's overhead restraint is for."""

    def render(self):
        return (cube([3, 2, 2]).translate([4.5, 0, 5.5])       # shelf
                + cube([2, 2, 2]).translate([5.5, 0, 4])       # tongue
                + cube([2, 2, 6]).translate([7, 0, 4]))        # body
