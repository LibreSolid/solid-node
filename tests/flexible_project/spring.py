# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import cadquery
from molejo import Circle, Helix, Line, P, Shape
from solid2 import cube

from solid_node.math import cos
from solid_node.node import (AssemblyNode, CadQueryNode, MolejoNode,
                             TranslationalPort)
from solid_node.simulation import Driver

#: The spring at rest, and how far the valve may push it down.
FREE_HEIGHT = 46.8
MAX_LIFT = 12.0

WIRE_RADIUS = 2.0
COIL_RADIUS = 14.0
TURNS = 6.5
PATH_SAMPLES = 240
PROFILE_SAMPLES = 16

#: A straight run, whose swept volume has a closed form to check against.
CABLE_RADIUS = 3.0
CABLE_PROFILE_SAMPLES = 64


class Spring(MolejoNode):
    """The valve spring: a circular wire swept along a helix whose height
    is the one thing the valvetrain moves."""

    height = TranslationalPort(unit='mm')

    def render(self):
        return Shape(
            profile=Circle(radius=WIRE_RADIUS),
            path=[Helix(radius=COIL_RADIUS, turns=TURNS, height=P.height)],
            path_samples=PATH_SAMPLES,
            profile_samples=PROFILE_SAMPLES,
        )


class Cable(MolejoNode):
    """A straight run of cable: a right circular cylinder, so the mesh's
    volume can be compared with an analytic value."""

    length = TranslationalPort(unit='mm')

    def render(self):
        return Shape(
            profile=Circle(radius=CABLE_RADIUS),
            path=[Line(to=[0, 0, P.length])],
            path_samples=2,
            profile_samples=CABLE_PROFILE_SAMPLES,
        )


class UnportedSpring(MolejoNode):
    """A shape naming a parameter no declared port carries."""

    def render(self):
        return Shape(
            profile=Circle(radius=WIRE_RADIUS),
            path=[Helix(radius=COIL_RADIUS, turns=TURNS, height=P.height)],
            path_samples=PATH_SAMPLES,
            profile_samples=PROFILE_SAMPLES,
        )


class WrongBackendSpring(MolejoNode):
    """A flexible leaf whose render() left the molejo namespace."""

    height = TranslationalPort(unit='mm')

    def render(self):
        return cube(4, center=True)


class Retainer(CadQueryNode):
    """The rigid part the spring pushes against: an ordinary exact leaf,
    so the tree holds a cached artifact beside the snapshot."""

    def render(self):
        return (cadquery.Workplane('XY')
                .circle(COIL_RADIUS + WIRE_RADIUS)
                .circle(COIL_RADIUS - WIRE_RADIUS)
                .extrude(3))


class Valvetrain(AssemblyNode):
    """The wiring: one driver, an expression over it, and an ordinary
    connect() into the spring's port."""

    lift = Driver(default=0.0, range=(0.0, MAX_LIFT), unit='mm')

    def __init__(self):
        self.retainer = Retainer()
        self.spring = Spring()
        super().__init__()

    def render(self):
        self.connect(FREE_HEIGHT - self.lift, self.spring.height)
        self.retainer.translate([0, 0, FREE_HEIGHT - self.lift])
        return [self.retainer, self.spring]


class Engine(AssemblyNode):
    """A root above the valvetrain, so the spring's parameter expression
    carries a QUALIFIED driver id the way a real machine's would."""

    def __init__(self):
        self.valvetrain = Valvetrain()
        super().__init__()

    def render(self):
        return [self.valvetrain]


class TimedValvetrain(AssemblyNode):
    """The wiring a running engine actually has: valve lift follows the
    crank, so the spring's port carries an expression over animation
    time rather than over a driver. Nothing binds `$t` on the build
    path, so this is the tree with no instant to photograph."""

    def __init__(self):
        self.retainer = Retainer()
        self.spring = Spring()
        super().__init__()

    def _lift(self):
        return MAX_LIFT * (1 - cos(720.0 * self.time)) / 2

    def render(self):
        lift = self._lift()
        self.connect(FREE_HEIGHT - lift, self.spring.height)
        self.retainer.translate([0, 0, FREE_HEIGHT - lift])
        return [self.retainer, self.spring]


class TimedEngine(AssemblyNode):
    """A root above the time-fed valvetrain."""

    def __init__(self):
        self.valvetrain = TimedValvetrain()
        super().__init__()

    def render(self):
        return [self.valvetrain]


class UnboundSpringMachine(AssemblyNode):
    """A spring whose port no connect() binds: the case that must still
    fail loudly rather than assemble into an empty leaf."""

    def __init__(self):
        self.spring = Spring()
        super().__init__()

    def render(self):
        return [self.spring]
