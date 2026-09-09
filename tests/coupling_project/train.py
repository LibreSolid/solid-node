# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The two shapes the coupling cycle is answerable to.

`Train` is wall clock 01: three arbors meshed in a row, the relations
written POWER-first because that is the order the train is built in, and
only the escape wheel bound -- so the whole train has to be solved
BACKWARDS through the inverse of a law the project wrote. `mesh` is that
law, a plain function of the two realized arbors reading the tooth
counts and the registration off them, exactly as the clock's
`going_train` reads them off its built library movement.

`Arm`/`Upper`/`Art3` is Thor: a root driver reaching a joint two levels
down by path with no port forwarded on the way, a derived coordinate
(`art3.elbow - shoulder`, the elbow belt anchored on the shoulder
housing) driving a pulley, and the pulley driving a belt through a pitch
arc. `Wrist` is Thor's differential, two formulas over the same pair.
"""

import math

from solid_node.motion.couplings import Affine
from solid_node.motion.joints import Revolute
from solid_node.node import AssemblyNode
from solid_node.parameters import Angle, Count
from solid_node.simulation import Driver

from .parts import Belt, Link, Pulley, Rod, Wheel

# Where each arbor's bearing sits, so every arbor turns about its own
# placed origin.
BEARING_PITCH = 12.0

# Millimetres of belt per degree of a 20 mm pitch-radius pulley.
PITCH_ARC = 2 * math.pi * 20.0 / 360.0


def mesh(driver, driven):
    """The law of one gear pair, as project code.

    Called once per realized parent with the two REALIZED arbors, so the
    tooth counts and the registration are read off the machine rather
    than passed down to it. The ratio is negative because an external
    pair reverses.
    """
    return Affine(ratio=-driver.wheel_teeth / driven.pinion_teeth,
                  offset=driven.registration)


class Arbor(AssemblyNode):
    """One arbor: a wheel, a pinion and the parts that turn with it."""

    index = Count(0, min=0)
    wheel_teeth = Count(60, min=1)
    pinion_teeth = Count(8, min=1)
    registration = Angle(0.0)

    turn = Revolute(axis=(0, 0, 1),
                    at=lambda node: (0.0, BEARING_PITCH * node.index, 0.0),
                    unit='deg')

    wheel = Wheel(turn=turn)
    rod = Rod(turn=turn)

    def render(self):
        self.wheel.translate([0.0, BEARING_PITCH * self.index, 0.0])
        self.rod.translate([0.0, BEARING_PITCH * self.index, 0.0])


class Train(AssemblyNode):
    """Three arbors, meshed power-first, driven from the escapement."""

    escape_angle = Driver(default=0.0, unit='deg')

    power = Arbor(index=0, wheel_teeth=60, pinion_teeth=8)
    centre = Arbor(index=1, wheel_teeth=48, pinion_teeth=8, registration=3.0)
    escape = Arbor(index=2, wheel_teeth=30, pinion_teeth=6, registration=5.0)

    power.drives(centre, law=mesh)
    centre.drives(escape, law=mesh)

    def simulate(self):
        self.escape.turn = self.escape_angle


class BackwardsTrain(AssemblyNode):
    """The same train, its relations written escape-first: the fixpoint
    makes the two indistinguishable."""

    escape_angle = Driver(default=0.0, unit='deg')

    power = Arbor(index=0, wheel_teeth=60, pinion_teeth=8)
    centre = Arbor(index=1, wheel_teeth=48, pinion_teeth=8, registration=3.0)
    escape = Arbor(index=2, wheel_teeth=30, pinion_teeth=6, registration=5.0)

    centre.drives(escape, law=mesh)
    power.drives(centre, law=mesh)

    def simulate(self):
        self.escape.turn = self.escape_angle


class Art3(AssemblyNode):
    """The forearm: one joint, reached from the root by path."""

    elbow = Revolute(axis=(0, 0, 1), unit='deg')

    link = Link()


class Upper(AssemblyNode):
    """The upper arm: its own shoulder joint, the forearm below it, and
    the elbow belt anchored on the shoulder housing."""

    shoulder = Revolute(axis=(0, 0, 1), unit='deg')

    art3 = Art3()
    pulley = Pulley()
    belt = Belt()

    relative = art3.elbow - shoulder

    relative.drives(pulley.turn)
    pulley.turn.drives(belt.travel, ratio=PITCH_ARC)


class Arm(AssemblyNode):
    """The root: three drivers, one of which reaches a joint two levels
    down with no port forwarded on the way."""

    shoulder_driver = Driver(default=0.0, unit='deg')
    elbow_driver = Driver(default=0.0, unit='deg')
    tool_driver = Driver(default=0.0, unit='deg')

    upper = Upper()

    shoulder_driver.drives(upper.shoulder)
    elbow_driver.drives(upper.art3.elbow)


class Wrist(AssemblyNode):
    """Thor's differential: two formulas over the same pair."""

    wrist_angle = Driver(default=0.0, unit='deg')
    tool_angle = Driver(default=0.0, unit='deg')

    wrist = Revolute(axis=(0, 0, 1), unit='deg')
    tool = Revolute(axis=(0, 1, 0), unit='deg')

    left = wrist + 2 * tool
    right = wrist - 2 * tool

    def simulate(self):
        self.wrist = self.wrist_angle
        self.tool = self.tool_angle
