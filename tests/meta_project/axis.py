# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Fixture for scenario testing: a driven axis with something to hit.

Two cubes and one stepper. The carriage rides ahead of a fixed stop
with 1mm of clearance when the axis is home, so the homing scenario
must stay clear all the way in and the crash instruction, which
deliberately drives past the declared travel, must be caught by the
cadence assertion at the tick the overlap appears. Geometry fidelity
is beside the point; what the fixture has to provide is a mesh
question a scenario can genuinely get wrong.

The declared defaults are bound in __init__ because a build path --
`solid test` builds the node before any test class runs -- has no
simulation to bind them for it. Binding defaults in the build and
viewer paths is a later stage of ADR-056; until then an assembly whose
render() reads a driver states its own opening snapshot.
"""

from solid_node.node import AssemblyNode
from solid_node.simulation import Driver, Instruction
from solid_node.simulation.driver import declared_drivers

from .parts import Cube

# GT2 belt on a 20-tooth pulley: 40mm/rev over 200 steps x 16 microsteps.
MM_PER_USTEP = 40.0 / (200 * 16)


class Axis(AssemblyNode):
    """A microstep-counting carriage, home at 10mm of travel."""

    x = Driver(default=800, range=(0, 8000), unit='ustep', dtype=int,
               scale=MM_PER_USTEP)

    instructions = {
        'Home': Instruction({'x': 0.0}, duration=2.0),
        # Past the declared travel and into the stop: a crash is an
        # instruction the machine will happily accept.
        'Crash': Instruction({'x': -5.0}, duration=2.0),
    }

    def __init__(self):
        self.stop = Cube(size=4.0)
        self.carriage = Cube(size=6.0)
        super().__init__()
        self.set_state(**{name: driver.default for name, driver
                          in declared_drivers(type(self)).items()})

    def render(self):
        self.carriage.translate(
            [self.state['x'] * MM_PER_USTEP + 6.0, 0, 0])
        return [self.stop, self.carriage]
