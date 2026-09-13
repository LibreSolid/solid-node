# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The tiny machines the running mode is answerable to.

`TrainBody` is the shape the Curta bench has: a crank driving a train of
arbors through affine ratios, a lever driving a slide through a project
law with a KINK (`clamp01`), the root's own joint wired down into a
child's plain port, and two instructions -- one absolute, one relative.
It declares NO time base, so the same class poses untimed exactly as it
always did; `Train` and `LoopingTrain` are the two bases over it.

The rest of the module is one machine per refusal or per propagation
shape the cycle states: backward propagation, a conflicting rigid group,
a jump, a law that is not an expression, an author binding of a run-owned
coordinate, a guarded rest default, an opaque source, a declared range,
an unbound coordinate, a partially bound `Free`, and the plain port an
author's `simulate()` keeps in step with a run-owned coordinate.
"""

import math

from solid_node.math import clamp01, floor
from solid_node.motion.joints import Free, Revolute
from solid_node.motion.ports import RotationalPort, Time
from solid_node.node import AssemblyNode
from solid_node.simulation import Driver, Instruction

from .parts import Arbor, Block, Slide, Wheel


def tooth_window(source, target):
    """The Curta bench's law, as project code: the pinion turns 72
    degrees while the tooth is engaged and holds outside the window."""
    return lambda angle: 4 + 72 * clamp01((angle - 113.5) / 11.25)


def periodic_window(source, target):
    """The same window made periodic -- which is the `floor` the running
    mode refuses until jumps land (cycle 2)."""
    return lambda angle: 4 + 72 * clamp01(
        (angle - 360 * floor(angle / 360) - 113.5) / 11.25)


def stdlib_law(source, target):
    """A law over Python's own `math`: it cannot be applied to a
    symbol."""
    return lambda angle: 10 * math.sin(angle)


class TrainBody(AssemblyNode):
    """The machine, with no time base of its own."""

    crank = Driver(default=0.0, unit='deg')
    lever = Driver(default=100.0, range=(100, 140), unit='deg')

    spindle = Revolute(axis=(0, 0, 1), unit='deg')

    first = Arbor()
    second = Arbor()
    slide = Slide()
    wheel = Wheel(turn=spindle)

    crank.drives(first.turn, ratio=2.0)
    first.turn.drives(second.turn, ratio=-1.5)
    lever.drives(slide.travel, law=tooth_window)
    crank.drives(spindle, ratio=1.0)

    instructions = {
        'Park': Instruction({'crank': 40.0}, duration=0.5),
        'Advance': Instruction(by={'crank': 10.0}, duration=0.5),
        'Wind': Instruction(by={'crank': 10.0, 'lever': 5.0}, duration=0.5),
    }

    def render(self):
        self.second.translate([30.0, 0.0, 0.0])
        self.slide.translate([0.0, 40.0, 0.0])
        self.wheel.translate([0.0, -40.0, 0.0])


class Train(TrainBody):
    """The same machine, running."""

    time = Time.running()


class LoopingTrain(TrainBody):
    """The same machine, looping: the base this cycle leaves alone."""

    time = Time(loop=2.0)


class Backwards(AssemblyNode):
    """A relation the rest render solves BACKWARD: `second.turn` is the
    source as written and the driven end is what the crank reaches."""

    time = Time.running()

    crank = Driver(default=0.0, unit='deg')

    first = Arbor()
    second = Arbor()

    crank.drives(first.turn, ratio=2.0)
    second.turn.drives(first.turn, ratio=4.0)

    def render(self):
        self.second.translate([30.0, 0.0, 0.0])


class Differential(AssemblyNode):
    """Two inputs prescribing one rigid group through a linear formula:
    the one conflict this cycle can reach."""

    time = Time.running()

    wrist_in = Driver(default=0.0, unit='deg')
    sum_in = Driver(default=0.0, unit='deg')

    wrist = Revolute(axis=(0, 0, 1), unit='deg')
    tool = Revolute(axis=(0, 1, 0), unit='deg')

    left = wrist + 2 * tool

    wrist_in.drives(wrist)
    wrist.drives(tool, ratio=1.0)
    sum_in.drives(left)

    block = Block()


class Stepped(AssemblyNode):
    """A running root whose law contains a jump."""

    time = Time.running()

    crank = Driver(default=0.0, unit='deg')
    first = Arbor()

    crank.drives(first.turn, law=periodic_window)


class SteppedBody(AssemblyNode):
    """The same machine with no time base: it poses untimed unchanged."""

    crank = Driver(default=0.0, unit='deg')
    first = Arbor()

    crank.drives(first.turn, law=periodic_window)


class Stdlib(AssemblyNode):
    """A running root whose law calls Python's own `math`."""

    time = Time.running()

    crank = Driver(default=0.0, unit='deg')
    first = Arbor()

    crank.drives(first.turn, law=stdlib_law)


class StdlibBody(AssemblyNode):
    """The same machine with no time base."""

    crank = Driver(default=0.0, unit='deg')
    first = Arbor()

    crank.drives(first.turn, law=stdlib_law)


class HandBound(AssemblyNode):
    """A law stated imperatively in `simulate()`: the run owns
    `first.turn`, so this is a double binding."""

    time = Time.running()

    crank = Driver(default=0.0, unit='deg')
    first = Arbor()

    def simulate(self):
        self.first.turn = self.crank * 2


class Guarded(AssemblyNode):
    """The catalogue's rest-default idiom: it binds once, at the rest
    render, and never again while the run owns the coordinate."""

    time = Time.running()

    crank = Driver(default=0.0, unit='deg')
    first = Arbor()
    slide = Slide()

    crank.drives(first.turn, ratio=2.0)

    def render(self):
        self.slide.translate([0.0, 40.0, 0.0])

    def simulate(self):
        if self.slide.travel.value is None:
            self.slide.travel = 4.0


class Opaque(AssemblyNode):
    """A relation into a bank coordinate sourced from a plain port the
    author's `simulate()` binds."""

    time = Time.running()

    crank = Driver(default=0.0, unit='deg')
    relay = RotationalPort(unit='deg')
    first = Arbor()

    relay.drives(first.turn, ratio=1.0)

    def simulate(self):
        self.relay = self.crank * 3


class OpaqueBody(AssemblyNode):
    """The same machine with no time base."""

    crank = Driver(default=0.0, unit='deg')
    relay = RotationalPort(unit='deg')
    first = Arbor()

    relay.drives(first.turn, ratio=1.0)

    def simulate(self):
        self.relay = self.crank * 3


class Ranged(AssemblyNode):
    """A joint whose declared range the crank drives it out of."""

    time = Time.running()

    crank = Driver(default=0.0, unit='deg')
    first = Arbor(turn=Revolute(axis=(0, 0, 1), range=(-90, 90), unit='deg'))

    crank.drives(first.turn, ratio=2.0)


class Unbound(AssemblyNode):
    """A joint nothing drives and no `simulate()` binds."""

    time = Time.running()

    crank = Driver(default=0.0, unit='deg')
    first = Arbor()
    idle = Arbor()

    crank.drives(first.turn, ratio=2.0)

    def render(self):
        self.idle.translate([30.0, 0.0, 0.0])


class Chassis(AssemblyNode):
    """A body floating against the world: six freedoms, one joint."""

    pose = Free(at=(0, 0, 0))
    block = Block()


class Sixfree(AssemblyNode):
    """Four of the six bound by relations, two left to the open question
    of design.md section 2."""

    time = Time.running()

    lift = Driver(default=0.0, unit='mm')
    surge = Driver(default=0.0, unit='mm')
    sway = Driver(default=0.0, unit='mm')
    heading = Driver(default=0.0, unit='deg')

    chassis = Chassis()

    lift.drives(chassis.pose.z)
    surge.drives(chassis.pose.x)
    sway.drives(chassis.pose.y)
    heading.drives(chassis.pose.yaw)


class Readout(AssemblyNode):
    """The Pascaline module's idiom: a plain port an author's
    `simulate()` keeps in step with a coordinate an ANCESTOR bound."""

    turn = Revolute(axis=(0, 0, 1), unit='deg')
    readout = RotationalPort(unit='deg')

    block = Block()

    def simulate(self):
        self.readout = self.turn.value


class Follower(AssemblyNode):
    """A running root holding one."""

    time = Time.running()

    crank = Driver(default=0.0, unit='deg')

    first = Arbor()
    gauge = Readout()

    crank.drives(first.turn, ratio=2.0)
    crank.drives(gauge.turn, ratio=2.0)

    def render(self):
        self.gauge.translate([0.0, 60.0, 0.0])


class BackDriven(AssemblyNode):
    """A relation whose driven end an author's `simulate()` binds and
    whose source is a joint coordinate: the rest render solves it
    BACKWARD, so a run that owns the source makes reading it backwards a
    double binding. No time base: the rule is the binder's, not the
    base's."""

    gauge = RotationalPort(unit='deg')
    first = Arbor()

    first.turn.drives(gauge, ratio=1.0)

    def simulate(self):
        self.gauge = 7.0
