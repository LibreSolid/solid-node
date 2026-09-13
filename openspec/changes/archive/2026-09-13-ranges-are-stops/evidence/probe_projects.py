# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Task 6.2: the two originating projects' own shapes, copied VERBATIM,
still compile and integrate -- and the Pascaline module's input arbor,
with the ratchet bound ADDED, blocks reverse where design.md section 11
says it does.

Nothing here is edited and nothing is written back. The law bodies are
cycle 2's, character-for-character the committed ones, from

* `projects/Calculators/Curta-Type-I-3x/simulation/input_mesh.py`
  (`input_step`), made periodic exactly as the pilot's illustration
  states it;
* `projects/Calculators/Pascaline-module/simulation/carry.py`
  (`handed_on`, `carried_column`) over the constants of
  `simulation/layout.py`, unchanged.

The RATCHET is the one thing this probe adds, and it adds it HERE rather
than in the project: the module's `InputArbor` declares
`turn = Revolute(axis=(1, 0, 0))` with no range, its `Ratchet10` has ten
teeth, and the one line the module will add in its own repository is the
bound below. The chain it drives -- `input.turn` -> `drum.turn` at -1 ->
`carry.turn` at -1 -- is the module's own.

Run from the worktree:

    PYTHONPATH="$PWD" python \
        openspec/changes/ranges-are-stops/evidence/probe_projects.py
"""

from solid2 import cylinder

from solid_node.math import clamp01, floor
from solid_node.motion.joints import Revolute
from solid_node.motion.ports import Time
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.simulation import Driver, Sim


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
    turns = floor((wheel - CARRY_OPEN) / 360.0)
    phase = wheel - 360.0 * turns
    advance = CARRY_THROW * turns
    for start, width, rise in CARRY_SEGMENTS:
        advance = advance + rise * clamp01((phase - start + CARRY_LEAD) / width)
    return advance


def carried_column(sources, driven):
    return lambda entry, below: DIGIT_STEP * entry + handed_on(below)


##############################################
# The smallest machines that state them


class Arbor(Solid2Node):
    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cylinder(r=10, h=4)


class Shaft(Solid2Node):
    """Geometry with nothing that moves: the arbors below own their own
    joint, so their parts must not own another."""

    def render(self):
        return cylinder(r=4, h=20)


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

    column.drives(units.turn, ratio=1.0)
    (entry & units.turn).drives(tens.turn, law=carried_column)

    def render(self):
        self.tens.translate([30.0, 0.0, 0.0])


class InputArbor(AssemblyNode):
    """The module's own arbor, with the ONE line it will add: the
    ratchet's ten teeth as the lower bound of its own coordinate."""

    turn = Revolute(axis=(1, 0, 0),
                    range=(lambda turn: DIGIT_STEP * floor(turn / DIGIT_STEP),
                           None))
    shaft = Shaft()


class DrumArbor(AssemblyNode):
    turn = Revolute(axis=(1, 0, 0))
    shaft = Shaft()


class CarryArbor(AssemblyNode):
    turn = Revolute(axis=(1, 0, 0))
    shaft = Shaft()


class DecimalModule(AssemblyNode):
    """The module's own chain, driven by a Driver where the committed
    module has a plain port an ancestor binds."""

    time = Time.running()

    angle = Driver(default=0, range=(0, 360), unit='deg')

    input = InputArbor()
    drum = DrumArbor()
    carry = CarryArbor()

    angle.drives(input.turn, ratio=1.0)
    input.turn.drives(drum.turn, ratio=-1)
    drum.turn.drives(carry.turn, ratio=-1)

    def render(self):
        self.drum.translate([0.0, 30.0, 0.0])
        self.carry.translate([0.0, 60.0, 0.0])


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
    print(f'  stops: {sim.stops}')

    print("\nthe Pascaline module's carry, over its own constants")
    sim = Sim(Column(), 1.0, record=8)
    rest = sim.state['tens.turn']
    sim.move('column', by=360, duration=36.0)
    sim.run(36.0)
    one = sim.state['tens.turn'] - rest
    print(f'  one column revolution   tens.turn +{one!r}')
    print(f'  against CARRY_THROW {CARRY_THROW}: '
          f'deficit {CARRY_THROW - one!r}')
    print(f'  stops: {sim.stops}')

    print("\nthe module's own chain WITH the ratchet bound, dt = 0.1")
    print(f'  the tooth is {DIGIT_STEP} degrees, ten of them')
    print('  each row of design.md section 11, from its own start:')
    print(f'  {"start":>6s} {"request":>8s} {"bound":>6s} {"t*":>5s} '
          f'{"admitted":>9s} {"status":>10s} {"turn after":>11s} '
          f'{"drum after":>11s}')
    for start, travel in ((40.0, 20.0), (40.0, -10.0), (36.0, -10.0),
                          (36.0, 4.0), (40.0, -10.0), (75.0, -10.0)):
        sim = Sim(DecimalModule(), 0.1, record=8, state={'angle': start})
        bound = sim._run._bounds()[0][1]
        handle = sim.move('angle', by=travel, duration=0.1)
        sim.run(0.1)
        stop = sim.stops[-1] if sim.stops else None
        print(f'  {start:6.1f} {travel:+8.1f} {bound:6.1f} '
              f'{(f"{stop.t:.4g}" if stop else "-"):>5s} '
              f'{handle.admitted:+9.2f} {handle.status:>10s} '
              f'{sim.state["input.turn"]:11.2f} '
              f'{sim.state["drum.turn"]:11.2f}'
              + (f'   blocked {stop.inputs}' if stop else ''))

    print('\n  read down rows 3-5: retention. And the same reverse at three')
    print('  cadences, which is the cadence independence a stop must have:')
    for duration, ticks in ((0.1, 1), (0.4, 4), (4.0, 40)):
        sim = Sim(DecimalModule(), 0.1, record=64, state={'angle': 40.0})
        handle = sim.move('angle', by=-10.0, duration=duration)
        sim.run(duration)
        stop, = sim.stops
        print(f'  {ticks:2d} tick(s) of {-10.0 / ticks:+6.3f}: blocking tick '
              f'{stop.tick:2d}, t* {stop.t!r:20s} input.turn '
              f'{sim.state["input.turn"]!r:6s} admitted {handle.admitted!r}')

    print('\n  and the tooth advances with the arbor:')
    sim = Sim(DecimalModule(), 0.1, record=8, state={'angle': 75.0})
    handle = sim.move('angle', by=-10.0, duration=0.1)
    sim.run(0.1)
    stop, = sim.stops
    print(f'  from 75  reverse by -10  input.turn = '
          f'{sim.state["input.turn"]!r}   {handle.status} admitted '
          f'{handle.admitted!r}   bound {stop.value!r}')


if __name__ == '__main__':
    main()
