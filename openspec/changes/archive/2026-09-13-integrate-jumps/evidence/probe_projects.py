# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Task 6.2: the two originating projects' own laws, copied VERBATIM,
compile and integrate.

Nothing here is edited and nothing is written back: the two law bodies
below are character-for-character the committed ones, from

* `projects/Calculators/Curta-Type-I-3x/simulation/input_mesh.py`
  (`input_step`), made periodic exactly as the pilot's illustration
  states it -- which is the edit that project will make in its own
  repository, and the reason this cycle exists;
* `projects/Calculators/Pascaline-module/simulation/carry.py`
  (`handed_on`, `carried_column`) over the constants of
  `simulation/layout.py`, unchanged.

Run from the worktree:

    PYTHONPATH="$PWD" python openspec/changes/integrate-jumps/evidence/probe_projects.py
"""

from solid_node.math import clamp01, floor
from solid_node.motion.joints import Revolute
from solid_node.motion.ports import Time
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.simulation import Driver, Sim

from solid2 import cylinder


##############################################
# The Curta bench's law, made periodic

def input_step(source, target):
    return lambda angle: 4 + 72 * clamp01((angle - 113.5) / 11.25)


def periodic_input_step(source, target):
    return lambda angle: 4 + 72 * clamp01(
        (angle - 360 * floor(angle / 360) - 113.5) / 11.25)


##############################################
# The Pascaline module's law, over its own constants

DIGIT_STEP = 36.0
CARRY_OPEN = 115.00
CARRY_THROW = 65.54
CARRY_SEGMENTS = ((115.0, 3.0, 4.10),
                  (118.0, 6.0, 6.74),
                  (124.0, 48.0, 47.88),
                  (172.0, 6.0, 4.82),
                  (178.0, 2.0, 1.28),
                  (180.0, 1.0, 0.58),
                  (181.0, 1.0, 0.14))
CARRY_LEAD = 0.10


def handed_on(wheel):
    """How far this column's four teeth have driven the next column's
    register."""
    turns = floor((wheel - CARRY_OPEN) / 360.0)
    phase = wheel - 360.0 * turns
    advance = CARRY_THROW * turns
    for start, width, rise in CARRY_SEGMENTS:
        advance = advance + rise * clamp01((phase - start + CARRY_LEAD) / width)
    return advance


def carried_column(sources, driven):
    """This column's own dial, plus whatever the column below has handed
    on."""
    return lambda entry, below: DIGIT_STEP * entry + handed_on(below)


def trailing_idler(source, driven):
    """The last column's idler: its own four teeth push it, nothing
    follows."""
    return lambda wheel: -handed_on(wheel)


##############################################
# The smallest machines that state them


class Arbor(Solid2Node):
    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cylinder(r=10, h=4)


class Curta(AssemblyNode):
    time = Time.running()

    crank_angle = Driver(default=100, unit='deg')
    pinion = Arbor()

    crank_angle.drives(pinion.turn, law=periodic_input_step)


class Column(AssemblyNode):
    time = Time.running()

    column = Driver(default=200.0, unit='deg')
    entry = Driver(default=0.0, unit='digit')

    units = Arbor()
    tens = Arbor()
    idler = Arbor()

    column.drives(units.turn, ratio=1.0)
    (entry & units.turn).drives(tens.turn, law=carried_column)
    units.turn.drives(idler.turn, law=trailing_idler)

    def render(self):
        self.tens.translate([30.0, 0.0, 0.0])
        self.idler.translate([60.0, 0.0, 0.0])


class Body(AssemblyNode):
    """The manifest's model: the framework discovers a root through one."""

    curta = Curta()

    def render(self):
        pass


def main():
    print("the Curta bench's law, made periodic -- dt = 1/240")
    sim = Sim(Curta(), 1 / 240, record=8)
    print(f'  rest                    pinion.turn = '
          f'{sim.state["pinion.turn"]!r}')
    for turn in (1, 2):
        sim.move('crank_angle', by=360, duration=1.0)
        sim.run(1.0)
        print(f'  after crank turn {turn}      pinion.turn = '
              f'{sim.state["pinion.turn"]!r}   crank '
              f'{sim.state["crank_angle"]!r}')
    print(f'  crossings: '
          f'{[(c.primitive, c.level, round(c.t, 6)) for c in sim.crossings]}')

    print("\nthe Pascaline module's handed_on, over its own constants")
    sim = Sim(Column(), 1.0, record=8)
    rest = sim.state['tens.turn']
    idle = sim.state['idler.turn']
    print(f'  rest                    tens.turn = {rest!r}   '
          f'idler.turn = {idle!r}')
    sim.move('column', by=360, duration=36.0)
    sim.run(36.0)
    one = sim.state['tens.turn'] - rest
    print(f'  one column revolution   tens.turn +{one!r}   '
          f'idler.turn {sim.state["idler.turn"] - idle!r}')
    sim.move('column', by=360, duration=36.0)
    sim.run(36.0)
    print(f'  two column revolutions  tens.turn '
          f'+{sim.state["tens.turn"] - rest!r}')
    print(f'  against CARRY_THROW {CARRY_THROW}: deficit {CARRY_THROW - one!r} '
          f'= first_rise * lead / first_width = '
          f'{4.10 * CARRY_LEAD / 3.0!r}')
    sim.move('entry', by=1.0, duration=1.0)
    sim.run(1.0)
    print(f'  one digit entered       tens.turn '
          f'+{sim.state["tens.turn"] - rest!r}')


if __name__ == '__main__':
    main()
