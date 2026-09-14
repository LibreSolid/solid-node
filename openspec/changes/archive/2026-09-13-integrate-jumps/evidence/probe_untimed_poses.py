# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Task 1.10: every new fixture POSES UNTIMED, and must go on posing
exactly so. A jump law's untimed reading is not this cycle's business.

Run from the worktree:

    PYTHONPATH="$PWD" python openspec/changes/integrate-jumps/evidence/probe_untimed_poses.py
"""

from solid_node.motion.ports import get_coordinate
from solid_node.simulation import Sim
from tests.running_project import machine as M

# (class, driven coordinate, {driver: [values]})
CASES = (
    (M.SteppedBody, 'first.turn', 'crank',
     (0.0, 113.5, 115.0, 124.0, 125.5, 359.9, 360.0, 360.1, 480.0, 820.0)),
    (M.WindowBody, 'pinion.turn', 'crank',
     (100.0, 113.5, 115.0, 124.0, 125.5, 359.9, 360.0, 360.1, 460.0, 820.0)),
    (M.RemainderBody, 'pinion.turn', 'crank',
     (100.0, 113.5, 115.0, 359.9, 360.0, 360.1, 460.0, 820.0)),
    (M.WrappedBody, 'pinion.turn', 'crank',
     (100.0, 179.9, 180.0, 180.1, 540.0, 600.0)),
    (M.ReverserBody, 'pinion.turn', 'crank', (40.0, 49.9, 50.0, 50.1, 60.0)),
    (M.KinkedBody, 'pinion.turn', 'crank', (40.0, 49.9, 50.0, 50.1, 60.0)),
    (M.ThrowingBody, 'pinion.turn', 'crank', (40.0, 49.9, 50.0, 50.1, 60.0)),
    (M.AlternatingBody, 'pinion.turn', 'crank',
     (100.0, 460.0, 820.0, 1180.0, 1540.0)),
    (M.OnlyJumpsBody, 'dial.turn', 'turns', (0.0, 0.5, 1.0, 2.5)),
    (M.CrowdedBody, 'dial.turn', 'a', (0.0, 0.25, 1.0, 2.75)),
)

MULTI = (
    (M.ClutchBody, 'wheel.turn',
     ({'shaft': 10.0, 'sleeve': 0.0}, {'shaft': 14.0, 'sleeve': 0.0},
      {'shaft': 10.0, 'sleeve': 1.0}, {'shaft': 14.0, 'sleeve': 1.0})),
    (M.CarryBody, 'tens.turn',
     ({'column': 100.0}, {'column': 460.0}, {'column': 820.0},
      {'column': 460.0, 'tens_entry': 1.0})),
    (M.CarryLeadBody, 'tens.turn',
     ({'column': 100.0}, {'column': 460.0}, {'column': 820.0})),
    (M.SettledBody, 'dial.turn',
     ({'enabled': 0.0, 'turns': 0.0}, {'enabled': 1.0, 'turns': 0.0},
      {'enabled': 0.0, 'turns': 2.0})),
    (M.DivisorBody, 'dial.turn',
     ({'a': 10.0, 'b': -2.0}, {'a': 10.0, 'b': 3.0})),
    (M.NonAffineBody, 'dial.turn',
     ({'a': 10.0, 'b': 5.0}, {'a': 30.0, 'b': 5.0})),
    (M.PortDrivenBody, 'first.turn', ({'crank': 100.0}, {'crank': 460.0})),
    (M.PortDrivenJointBody, 'first.turn', ({'crank': 100.0}, {'crank': 460.0})),
    (M.PortDrivenSmoothBody, 'first.turn',
     ({'crank': 100.0}, {'crank': 125.5})),
)


def reads(node, qualified):
    *path, name = qualified.split('.')
    for step in path:
        node = getattr(node, step)
    return get_coordinate(node, name)._value


def main():
    for cls, coordinate, driver, values in CASES:
        for value in values:
            sim = Sim(cls(), 0.1, state={driver: value})
            print(f'{cls.__name__:<20} {driver}={value:<10} '
                  f'{coordinate} = {reads(sim.node, coordinate)!r}')
    for cls, coordinate, states in MULTI:
        for state in states:
            sim = Sim(cls(), 0.1, state=dict(state))
            shown = ' '.join(f'{k}={v}' for k, v in sorted(state.items()))
            print(f'{cls.__name__:<20} {shown:<28} '
                  f'{coordinate} = {reads(sim.node, coordinate)!r}')


if __name__ == '__main__':
    main()
