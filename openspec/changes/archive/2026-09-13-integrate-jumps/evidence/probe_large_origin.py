# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Task 2.12 and design.md section 11: what a periodic law loses at a
large origin, measured through the framework's own evaluator.

Two turns of the Curta window at dt = 1/240, from a crank already wound
`W` turns, against the identical run at zero winding.

Run from the worktree:

    PYTHONPATH="$PWD" python openspec/changes/integrate-jumps/evidence/probe_large_origin.py
"""

import math

from solid_node.simulation import Sim
from tests.running_project.machine import Window


def two_turns(winding, per_tick=False):
    sim = Sim(Window(), 1 / 240, state={'crank': winding * 360.0 + 100.0})
    if not per_tick:
        sim.move('crank', by=720, duration=2.0)
    trace = []
    for _ in range(480):
        if per_tick:
            # The other way to drive: a fresh one-tick move from where
            # the bank stands, rather than one absolute ramp.
            sim.move('crank', by=1.5, duration=1 / 240)
        sim.run(1 / 240)
        trace.append(sim.state['pinion.turn'])
    return sim, trace


reference = two_turns(0.0)[1]
print('| initial winding | crank magnitude | ulp | max per-tick deviation '
      '| pinion after two turns |')
print('| --- | --- | --- | --- | --- |')
print(f'| 0 | 100 | {math.ulp(100.0):.1e} | -- | {reference[-1]!r} |')
for winding in (1e3, 1e6, 1e9, 1e12, 1e13, 1e14):
    magnitude = winding * 360.0
    sim, trace = two_turns(winding)
    deviation = max(math.fabs(x - y) for x, y in zip(reference, trace))
    print(f'| 10^{round(math.log10(winding))} turns | {magnitude:.1e} | '
          f'{math.ulp(magnitude):.1e} | {deviation:.3e} | {trace[-1]!r} |')

print()
print('The same 1e14 winding driven tick by tick rather than by one ramp:')
sim, trace = two_turns(1e14, per_tick=True)
print(f'  crank asked for 1.5 degrees a tick, 480 times, from '
      f'{1e14 * 360.0 + 100.0!r}')
print(f'  crank now {sim.state["crank"]!r}  (ulp '
      f'{math.ulp(1e14 * 360.0):.1e})')
print(f'  pinion    {trace[-1]!r}')
