# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Thor's elbow, an arbor stack and a gantry: the three shapes the joint
cycle is answerable to.

`Arm`/`Forearm` are the originating evidence, with the numbers the
project has (`projects/Robotic-Arms/Thor/simulation/art2.py`): the
forearm is placed `rotate(90, [1, 0, 0])` then
`translate([0, 160 + 81.5, 68])`, and its elbow runs along the parent's
z through `(0, 160, 68)`. Carried into the forearm's own frame that is
the axis `(0, 1, 0)` about `(0, 0, 81.5)` the project wrote by hand.

`ArborStack`/`Arbor` is the clock: an anchor that comes off a built
library object rather than out of a formula, and one coordinate wired
down to the parts that turn with the arbor.

`Gantry`/`Carriage` is the slide.
"""

from solid_node.motion.joints import Revolute
from solid_node.node import AssemblyNode
from solid_node.parameters import Count, Length
from solid_node.simulation import Driver

from .parts import Carriage, Link, Rod, Wheel

# Thor's own constants: the elbow is 81.5 mm up the forearm and the
# shoulder 160 mm out along the upper arm.
ELBOW_ALONG_ARM = 160.0
ELBOW_ACROSS_ARM = 81.5
ELBOW_HEIGHT = 68.0

BEARING_PITCH = 12.0


class Forearm(AssemblyNode):
    """The moving body: it declares where it may move, in the frame its
    parent places it in."""

    reach = Length(ELBOW_ALONG_ARM, min=0)

    elbow = Revolute(axis=(0, 0, 1), at=(0, reach, ELBOW_HEIGHT),
                     range=(-135, 135), unit='deg')

    link = Link()


class Arm(AssemblyNode):
    """The parent: rest placement in render(), the elbow bound from a
    driver in simulate()."""

    reach = Length(ELBOW_ALONG_ARM, min=0)

    angle = Driver(default=0.0, unit='deg')

    forearm = Forearm(reach=reach)

    def render(self):
        self.forearm.rotate(90, [1, 0, 0])
        self.forearm.translate(
            [0, self.reach + ELBOW_ACROSS_ARM, ELBOW_HEIGHT])

    def simulate(self):
        self.forearm.elbow = self.angle


class _Movement:
    """A stand-in for the clock's built library movement: the bearing
    positions are a lookup into an object the node builds from its
    parameters, not a formula over declared tokens."""

    def __init__(self, count):
        self.bearings = [(0.0, BEARING_PITCH * index, 0.0)
                         for index in range(count)]


class Arbor(AssemblyNode):
    """One arbor turning at its own bearing, with the parts that turn
    with it wired to its coordinate."""

    index = Count(0, min=0)
    count = Count(3, min=1)

    turn = Revolute(axis=(0, 0, 1),
                    at=lambda node: node.built.bearings[node.index],
                    unit='deg')

    wheel = Wheel(turn=turn)
    rod = Rod(turn=turn)

    @property
    def built(self):
        return _Movement(self.count)


class ArborStack(AssemblyNode):
    """Two arbors, each placed at its own bearing, so each joint runs
    through the body's placed origin."""

    rotation = Driver(default=0.0, unit='deg')

    arbors = [Arbor(index=0), Arbor(index=1)]

    def render(self):
        for index, arbor in enumerate(self.arbors):
            arbor.translate([0.0, BEARING_PITCH * index, 0.0])

    def simulate(self):
        for arbor in self.arbors:
            arbor.turn = self.rotation


class Gantry(AssemblyNode):
    """The slide, turned a quarter turn by its rest placement so the
    carry has something to do."""

    offset = Driver(default=0.0, unit='mm')

    carriage = Carriage()

    def render(self):
        self.carriage.rotate(90, [0, 0, 1])

    def simulate(self):
        self.carriage.travel = self.offset
