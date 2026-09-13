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

The JUMP machines below are cycle 2's: one per jump primitive, one per
nesting and multi-source shape, one per refusal, and the two awkward
level quantities -- a moving divisor and a product of two sources -- the
crossing search has to answer for. Each running root subclasses an
untimed `...Body` twin, so the same law is read both ways and the
untimed reading is pinned by a control.
"""

import math

from solid_node.math import abs, clamp01, floor, sign, wrap
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
    """The same window made periodic: the pilot's illustration of the
    whole feature. The pinion turns 72 degrees once per crank
    revolution, and the `floor` that resets the phase is a jump the run
    locates inside the tick and subtracts."""
    return lambda angle: 4 + 72 * clamp01(
        (angle - 360 * floor(angle / 360) - 113.5) / 11.25)


def remainder_window(source, target):
    """The same window written with `%` instead of `floor`. `%` is
    `fmod`, so it takes the sign of the DIVIDEND and jumps at every
    NONZERO integer of `angle / 360` -- and over a forward crank the two
    spellings read the same at every tick."""
    return lambda angle: 4 + 72 * clamp01(((angle % 360) - 113.5) / 11.25)


def wrapped(source, target):
    """`wrap()` is a `ceil` and needs nothing of its own. Every branch
    of this law has slope 2, so its integrated reading is twice the
    UNWRAPPED travel."""
    return lambda angle: 2 * wrap(angle, 360.0)


def reversing(source, target):
    """A `sign` that does NOT jump: the factor it multiplies vanishes
    where it flips, so the law is continuous and must read exactly like
    its `abs` twin."""
    return lambda x: 5 * (x - 50.0) * sign(x - 50.0)


def kinked(source, target):
    """That twin, with no jump node in it at all."""
    return lambda x: 5 * abs(x - 50.0)


def throwing(source, target):
    """A `sign` that genuinely jumps -- by `10 * x` at the crossing --
    so the two segments contribute and the jump does not."""
    return lambda x: 5 * x * sign(x - 50.0)


def clutch(sources, target):
    """The spike's clutch, in the vocabulary this cycle admits: a GATE
    FACTOR in a multi-source law. Open, the wheel holds; closed, the
    pair drives; closing, the wheel takes the travel AFTER engagement
    and never the jump the gate would have applied."""
    return lambda shaft, sleeve: -2 * shaft * (sleeve > 0.5)


def alternating(source, target):
    """A jump node whose argument contains another: the engagement
    happens on alternate revolutions only. Mechanically it is the
    alternating engagement a Pascaline column chain has."""
    def law(angle):
        w = floor(angle / 360)
        even = 1 - (w - 2 * floor(w / 2))
        return 72 * clamp01((angle - 360 * w - 113.5) / 11.25) * even

    return law


# The Pascaline module's carry, with round constants of the fixture's
# own so the worked numbers are exact: a column hands on CARRY_THROW per
# revolution of the column below it, shaped by one `clamp01` segment per
# piece of the cam.
CARRY_OPEN = 100.0
CARRY_PERIOD = 360.0
CARRY_THROW = 60.0
CARRY_SEGMENTS = ((100.0, 10.0, 20.0), (110.0, 40.0, 40.0))
DIGIT_STEP = 36.0


def handed_on(wheel, lead):
    """What the column below hands on, in the module's own shape.

    A non-zero `lead` makes the law DISCONTINUOUS at the window
    boundary, by `first_rise * lead / first_width`: the phase resets
    while the lead-shifted first segment still reads part-way up its
    ramp. The integrated reading subtracts that jump, so the throw comes
    out below `CARRY_THROW` by exactly that much.
    """
    turns = floor((wheel - CARRY_OPEN) / CARRY_PERIOD)
    phase = wheel - CARRY_PERIOD * turns
    advance = CARRY_THROW * turns
    for start, width, rise in CARRY_SEGMENTS:
        advance = advance + rise * clamp01((phase - start + lead) / width)
    return advance


def carried_column(sources, driven):
    """The module's own multi-source column law: what this column is
    entered with, plus what the column below hands on."""
    return lambda entry, below: DIGIT_STEP * entry + handed_on(below, 0.0)


def carried_column_lead(sources, driven):
    """The same law with the module's own lead, which makes it jump."""
    return lambda entry, below: DIGIT_STEP * entry + handed_on(below, 0.5)


def counter(source, target):
    """A law that can move its coordinate ONLY by jumping: every jump is
    subtracted, so it can never move it at all."""
    return lambda turns: floor(turns)


def settled(sources, target):
    """The Curta carry bench's shape: a jump-only term beside a sloped
    one. It COMPILES -- `enabled` still carries slope -- and the running
    reading gives the turns nothing."""
    return lambda enabled, turns: 9 * enabled + floor(turns)


def moving_divisor(sources, target):
    """A `%` whose divisor moves: its level quantity `a / b` is not
    affine, and a tick whose path takes `b` through zero has no level at
    all."""
    return lambda a, b: 0.5 * a + (a % b)


def non_affine(sources, target):
    """A level quantity that is a PRODUCT of two sources, so the
    crossing is bracketed and bisected rather than solved."""
    return lambda a, b: a * floor(a * b / 100.0)


def crowded(source, target):
    """A sawtooth whose period is ONE unit: a coarse enough tick crosses
    more surfaces than the run admits."""
    return lambda a: clamp01(a - floor(a)) * 0.5


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


##############################################
# Cycle 2: the jump machines
#
# Each running root subclasses its own untimed `...Body`, so the one law
# is read both ways: untimed it poses absolutely, as it always did, and
# running it is integrated over the tick's segments.


class WindowBody(AssemblyNode):
    """The pilot's illustration, untimed: a crank and a pinion that
    turns 72 degrees once per revolution."""

    crank = Driver(default=100.0, unit='deg')
    pinion = Arbor()

    crank.drives(pinion.turn, law=periodic_window)


class Window(WindowBody):
    """The same machine, running."""

    time = Time.running()


class RemainderBody(AssemblyNode):
    """The same window written with `%`."""

    crank = Driver(default=100.0, unit='deg')
    pinion = Arbor()

    crank.drives(pinion.turn, law=remainder_window)


class Remainder(RemainderBody):
    time = Time.running()


class WrappedBody(AssemblyNode):
    """A `wrap`, which is a `ceil`."""

    crank = Driver(default=100.0, unit='deg')
    pinion = Arbor()

    crank.drives(pinion.turn, law=wrapped)


class Wrapped(WrappedBody):
    time = Time.running()


class ReverserBody(AssemblyNode):
    """A `sign` whose crossing contributes nothing."""

    crank = Driver(default=40.0, unit='deg')
    pinion = Arbor()

    crank.drives(pinion.turn, law=reversing)


class Reverser(ReverserBody):
    time = Time.running()


class KinkedBody(AssemblyNode):
    """Its continuous twin, with no jump node at all."""

    crank = Driver(default=40.0, unit='deg')
    pinion = Arbor()

    crank.drives(pinion.turn, law=kinked)


class Kinked(KinkedBody):
    time = Time.running()


class ThrowingBody(AssemblyNode):
    """A `sign` that genuinely jumps."""

    crank = Driver(default=40.0, unit='deg')
    pinion = Arbor()

    crank.drives(pinion.turn, law=throwing)


class Throwing(ThrowingBody):
    time = Time.running()


class AlternatingBody(AssemblyNode):
    """A jump nested in another jump's argument."""

    crank = Driver(default=100.0)
    pinion = Arbor()

    crank.drives(pinion.turn, law=alternating)


class Alternating(AlternatingBody):
    time = Time.running()


class ClutchBody(AssemblyNode):
    """The gate factor, over two sources and one joint path."""

    shaft = Driver(default=10.0, unit='deg')
    sleeve = Driver(default=0.0, unit='mm')
    wheel = Arbor()

    (shaft & sleeve).drives(wheel.turn, law=clutch)


class Clutch(ClutchBody):
    time = Time.running()


class CarryBody(AssemblyNode):
    """The Pascaline module's own shape: one driver and one JOINT
    COORDINATE as the two sources of a column's carry law."""

    column = Driver(default=100.0, unit='deg')
    tens_entry = Driver(default=0.0, unit='digit')

    units = Arbor()
    tens = Arbor()

    column.drives(units.turn, ratio=1.0)
    (tens_entry & units.turn).drives(tens.turn, law=carried_column)

    def render(self):
        self.tens.translate([30.0, 0.0, 0.0])


class Carry(CarryBody):
    time = Time.running()


class CarryLeadBody(AssemblyNode):
    """The same carry with the module's own lead, which makes the law
    jump at the window boundary."""

    column = Driver(default=100.0, unit='deg')
    tens_entry = Driver(default=0.0, unit='digit')

    units = Arbor()
    tens = Arbor()

    column.drives(units.turn, ratio=1.0)
    (tens_entry & units.turn).drives(tens.turn, law=carried_column_lead)

    def render(self):
        self.tens.translate([30.0, 0.0, 0.0])


class CarryLead(CarryLeadBody):
    time = Time.running()


class PortDrivenBody(AssemblyNode):
    """A jumping law driving a PLAIN PORT wired to a joint -- the
    Pascaline module's committed shape, and the one design.md section 9a
    refuses under a running root."""

    crank = Driver(default=100.0, unit='deg')
    register = RotationalPort(unit='deg')
    first = Arbor()

    register.drives(first.turn, ratio=1.0)
    crank.drives(register, law=periodic_window)


class PortDriven(PortDrivenBody):
    time = Time.running()


class PortDrivenJointBody(AssemblyNode):
    """The same relation stated into the joint coordinate the run owns,
    with the port following it: the migration the refusal asks for."""

    crank = Driver(default=100.0, unit='deg')
    register = RotationalPort(unit='deg')
    first = Arbor()

    crank.drives(first.turn, law=periodic_window)
    first.turn.drives(register, ratio=1.0)


class PortDrivenJoint(PortDrivenJointBody):
    time = Time.running()


class PortDrivenSmoothBody(AssemblyNode):
    """A CONTINUOUS law driving the same plain port: it compiles, so the
    refusal above is shown to be the jump's and not the port's."""

    crank = Driver(default=100.0, unit='deg')
    register = RotationalPort(unit='deg')
    first = Arbor()

    register.drives(first.turn, ratio=1.0)
    crank.drives(register, law=tooth_window)


class PortDrivenSmooth(PortDrivenSmoothBody):
    time = Time.running()


class OnlyJumpsBody(AssemblyNode):
    """A law that can only jump: arithmetic, not a mechanism."""

    turns = Driver(default=0.0)
    dial = Arbor()

    turns.drives(dial.turn, law=counter)


class OnlyJumps(OnlyJumpsBody):
    time = Time.running()


class SettledBody(AssemblyNode):
    """A jump-only term beside a sloped one: it compiles."""

    enabled = Driver(default=0.0)
    turns = Driver(default=0.0)
    dial = Arbor()

    (enabled & turns).drives(dial.turn, law=settled)


class Settled(SettledBody):
    time = Time.running()


class DivisorBody(AssemblyNode):
    """A `%` whose divisor a tick can take through zero."""

    a = Driver(default=10.0)
    b = Driver(default=-2.0)
    dial = Arbor()

    (a & b).drives(dial.turn, law=moving_divisor)


class Divisor(DivisorBody):
    time = Time.running()


class NonAffineBody(AssemblyNode):
    """A level quantity that is a product of two sources."""

    a = Driver(default=10.0)
    b = Driver(default=5.0)
    dial = Arbor()

    (a & b).drives(dial.turn, law=non_affine)


class NonAffine(NonAffineBody):
    time = Time.running()


class CrowdedBody(AssemblyNode):
    """A sawtooth of period one unit."""

    a = Driver(default=0.0)
    dial = Arbor()

    a.drives(dial.turn, law=crowded)


class Crowded(CrowdedBody):
    time = Time.running()


class PhaseCoupling:
    """A coupling whose INVERSE carries the jump.

    `inverse` folds the driven angle into one revolution -- what a phase
    reading is -- and `forward` is that inverse on the principal branch.
    The rest render solves the relation below backward, so the face the
    run compiles and integrates is the one with the `ceil` in it, over
    the DRIVEN end's id.
    """

    invertible = True

    def forward(self, phase):
        return phase

    def inverse(self, driven):
        return wrap(driven, 360.0)


def phase_coupling(source, target):
    return PhaseCoupling()


class BackwardJumpBody(AssemblyNode):
    """A relation the rest render solves BACKWARD, whose inverse jumps."""

    crank = Driver(default=100.0, unit='deg')

    first = Arbor()
    second = Arbor()

    crank.drives(first.turn, ratio=2.0)
    second.turn.drives(first.turn, law=phase_coupling)

    def render(self):
        self.second.translate([30.0, 0.0, 0.0])


class BackwardJump(BackwardJumpBody):
    time = Time.running()


class SmoothBody(AssemblyNode):
    """`Window`'s machine with the periodicity taken out: the same law,
    the same shape, and no jump node at all. It is the control the
    per-tick cost of a jump is measured against
    (`evidence/probe_cost.py`), which needs the two machines identical
    in everything but the `floor`."""

    crank = Driver(default=100.0, unit='deg')
    pinion = Arbor()

    crank.drives(pinion.turn, law=tooth_window)


class Smooth(SmoothBody):
    time = Time.running()
