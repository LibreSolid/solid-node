# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Task 2.14: what one tick of a JUMP-carrying law costs, beside cycle
1's own 1.16 ms on `Train`.

Design.md section 12 states two rules and one incidental saving:

1. a graph with no jump node takes cycle 1's path unchanged, so `Train`
   must come back within noise of the base number;
2. a crossing search never evaluates the whole law -- a segment endpoint
   is one skeleton evaluation, a branch sample one small argument
   evaluation per jump node;
3. `Run._values()` skips an edge whose targets are all bank keys, which
   removes one evaluation per law per tick from cycle 1's cost as well.

`Window` is measured twice: on a rate slow enough that no tick crosses a
window boundary, and on one fast enough that EVERY tick crosses one.

Run from the worktree:

    PYTHONPATH="$PWD" python openspec/changes/integrate-jumps/evidence/probe_cost.py
"""

import time
import tracemalloc

from solid_node.scad_expression import GraphValue
from solid_node.simulation import Sim
from tests.running_project.machine import (Smooth, Train, TrainBody,
                                           Window)

TICKS = 10_000


def measure(label, sim, ticks, prime=100):
    sim.run(prime * sim.dt)
    tracemalloc.start()
    started = time.perf_counter()
    sim.run(ticks * sim.dt)
    elapsed = time.perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f'{label}: {elapsed:.3f} s for {ticks} ticks '
          f'= {elapsed / ticks * 1e3:.3f} ms/tick, '
          f'tracemalloc peak {peak / 1024:.1f} KiB')
    return elapsed / ticks


running = Sim(Train(), 0.1)
running.rate('crank', 1.0)
train = measure('running  Train    no jump          ', running, TICKS)

untimed = Sim(TrainBody(), 0.1)
untimed.trigger('Park')
plain = measure('untimed  TrainBody                 ', untimed, TICKS)

# `Smooth` is `Window`'s machine with the periodicity taken out: the
# same law, the same shape, no jump node. It is what the two `Window`
# measurements below are answerable to.
smooth = Sim(Smooth(), 1 / 240)
smooth.rate('crank', 120.0)
continuous = measure('running  Smooth   no jump          ', smooth, TICKS)

# 0.5 degrees a tick from 100: the window boundary at 360 is crossed
# once in 520 ticks, so all but a handful of these cross nothing.
quiet = Sim(Window(), 1 / 240)
quiet.rate('crank', 120.0)
holding = measure('running  Window   no crossing      ', quiet, TICKS)

# 360 degrees a tick: the level quantity advances by exactly one, so
# every tick crosses exactly one boundary.
busy = Sim(Window(), 1 / 240)
busy.rate('crank', 360 * 240.0)
crossing = measure('running  Window   one crossing/tick', busy, TICKS)

print(f'\nWindow non-crossing / Smooth (same machine): {holding / continuous:.2f}x')
print(f'Window crossing     / Smooth (same machine): {crossing / continuous:.2f}x')
print(f'Window non-crossing / Train  (cycle 1 pin):  {holding / train:.2f}x')
print(f'Window crossing     / Train  (cycle 1 pin):  {crossing / train:.2f}x')
print(f'Train / untimed TrainBody:                   {train / plain:.2f}x')

# The one regression assertion of task 2.14: cycle 1 measured 1.173
# ms/tick on this worktree (evidence.md section 0.3), and design.md
# section 12 rule 1 says a graph with no jump node takes cycle 1's path
# unchanged.
BASE = 1.173e-3
assert train < 1.5 * BASE, (
    f'Train costs {train * 1e3:.3f} ms/tick against cycle 1\'s '
    f'{BASE * 1e3:.3f}: a law with no jump must take cycle 1\'s path '
    f'unchanged.')


##############################################
# The same thing deterministically: how many graph evaluations one tick
# takes. Wall clock says what a machine did today; this says what the
# engine asked for, and it is the same on any machine.


def evaluations(sim, ticks=1):
    counted = []
    original = GraphValue.evaluate
    GraphValue.evaluate = lambda self, inputs: (counted.append(1)
                                                or original(self, inputs))
    try:
        sim.run(ticks * sim.dt)
    finally:
        GraphValue.evaluate = original
    return len(counted)


print()
counting = Sim(Train(), 0.1)
counting.rate('crank', 1.0)
counting.run(0.1)
discarded = sum(1 for edge in counting.program.edges if edge.kind == 'law'
                for graph in edge.graphs if graph is not None)
print(f'Train  one tick, 4 law edges, no jump: '
      f'{evaluations(counting)} graph evaluations '
      f'({discarded} fewer than cycle 1, which evaluated every law edge '
      f'once more in _values() and discarded the result)')

counting = Sim(Smooth(), 1 / 240)
counting.rate('crank', 120.0)
counting.run(1 / 240)
print(f'Smooth one tick, 1 law edge,  no jump: '
      f'{evaluations(counting)} graph evaluations')

counting = Sim(Window(), 1 / 240)
counting.rate('crank', 120.0)
counting.run(1 / 240)
print(f'Window one tick, 1 law edge,  no crossing: '
      f'{evaluations(counting)} graph evaluations')

counting = Sim(Window(), 1 / 240)
counting.rate('crank', 360 * 240.0)
counting.run(1 / 240)
print(f'Window one tick, 1 law edge,  one crossing: '
      f'{evaluations(counting)} graph evaluations')
