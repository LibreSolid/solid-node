# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Thor's elbow, an arbor stack and a gantry: the three shapes the joint
cycle is answerable to.

`Arm`/`Forearm` are the originating evidence, with the numbers the
project has (`projects/Robotic-Arms/Thor/simulation/art2.py`): the
elbow is the forearm's OWN statement about itself, `axis=(0, 1, 0)`
about `(0, 0, 81.5)` -- `ELBOW_PIVOT_AXIS` and `ELBOW_PIVOT` in the
project's own `art2.py`, written here exactly where the project writes
them. The parent still places the forearm with `rotate(90, [1, 0, 0])`
then `translate([0, 160 + 81.5, 68])`, but that placement is the
forearm's REST frame, one step away from its parent's, and never enters
the joint's own arguments.

`ArborStack`/`Arbor` is the clock: each arbor turns on its own bearing
(`turn`, no anchor at all -- the bearing IS the arbor's own placed
origin, so restating it would only repeat what `ArborStack.render()`
already says) and one coordinate is wired down to the parts that turn
with it. `Arbor.pin` is the companion case: a point of the arbor that
is genuinely NOT its own origin -- a feature read off the arbor's own
built object, per instance -- which is why it still needs a callable
anchor once the bearing itself no longer does.

`Gantry`/`Carriage` is the slide, turned a quarter turn by its parent so
there is something for its own frame to differ from.
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
    """The moving body: it declares where it may move, in its OWN rest
    frame -- one rest placement away from wherever its parent puts it."""

    reach = Length(ELBOW_ALONG_ARM, min=0)

    elbow = Revolute(axis=(0, 1, 0), at=(0, 0, ELBOW_ACROSS_ARM),
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


class SiteArm(AssemblyNode):
    """The exact inverse of `Arm`: the SAME elbow, stated by the PARENT
    at the declaration site instead of by `Forearm`'s own class body.

    `Forearm` still declares `elbow` on its own class, in its own frame
    (`axis=(0, 1, 0), at=(0, 0, ELBOW_ACROSS_ARM)`); the site's
    `elbow=` REPLACES that declaration whole and keeps its slot (design
    decision 7). The physical line is the same one -- the elbow's own
    location, `ELBOW_ALONG_ARM` out along the upper arm and
    `ELBOW_HEIGHT` up -- now stated in the frame `SiteArm.render()`
    itself works in rather than in the forearm's own.
    """

    reach = Length(ELBOW_ALONG_ARM, min=0)

    angle = Driver(default=0.0, unit='deg')

    forearm = Forearm(
        reach=reach,
        elbow=Revolute(axis=(0, 0, 1),
                       at=(0, ELBOW_ALONG_ARM, ELBOW_HEIGHT),
                       range=(-135, 135), unit='deg'))

    def render(self):
        self.forearm.rotate(90, [1, 0, 0])
        self.forearm.translate(
            [0, self.reach + ELBOW_ACROSS_ARM, ELBOW_HEIGHT])

    def simulate(self):
        self.forearm.elbow = self.angle


class _Movement:
    """A stand-in for the clock's built library movement: the bearing
    positions are a lookup into an object the node builds from its
    parameters, not a formula over declared tokens.

    `pin` is a SECOND feature of the same built object, off the
    arbor's own bearing by a few millimetres that differ per instance --
    the case a callable anchor still earns its keep for, once the
    bearing itself no longer needs one."""

    def __init__(self, count):
        self.bearings = [(0.0, BEARING_PITCH * index, 0.0)
                         for index in range(count)]
        self.pin = [(0.0, 5.0 + index, 0.0) for index in range(count)]


class Arbor(AssemblyNode):
    """One arbor turning at its own bearing, with the parts that turn
    with it wired to its coordinate.

    `turn` needs no anchor at all: the bearing IS the arbor's own placed
    origin, so stating it would only restate what `ArborStack.render()`
    already says. `pin` is a second, genuinely off-origin freedom whose
    anchor still comes off the arbor's own built object, per instance --
    the callable-argument case `turn` used to be the fixture for."""

    index = Count(0, min=0)
    count = Count(3, min=1)

    turn = Revolute(axis=(0, 0, 1), unit='deg')
    pin = Revolute(axis=(1, 0, 0),
                    at=lambda node: node.built.pin[node.index],
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
