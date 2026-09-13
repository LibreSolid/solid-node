# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Task 6.1: what a stop costs, beside cycle 1's and cycle 2's own
per-tick numbers on the same host and method.

Design.md section 15 states four expectations:

1. a tick with NO stop pays what it pays today -- one inclusive
   comparison per ranged coordinate, plus one graph evaluation per tick
   for each EXPRESSION bound. `Train` has no ranged coordinate at all,
   so it must come back within noise of cycle 1's number;
2. a blocking tick on an AFFINE chain costs one division for the
   localization and two propagation passes instead of one, so under 3x
   one tick, ONCE, at the stop;
3. a blocking tick on a NON-AFFINE chain costs up to
   `_SUBDIVISIONS + _BISECTION_ROUNDS` EDGE evaluations -- not program
   passes -- plus the same two propagation passes;
4. the contribution test costs one sub-program propagation per PUSHING
   CANDIDATE, on a blocking tick only.

The blocking measurements are taken as a loop of `restore` + `move` +
`run` against the IDENTICAL loop with a move that does not reach the
bound, on the same machine: the restore and the command are common to
both, so the difference is the stop.

Run from the worktree:

    PYTHONPATH="$PWD" python \
        openspec/changes/ranges-are-stops/evidence/probe_stop_cost.py
"""

import time
import tracemalloc

from solid_node.scad_expression import GraphValue
from solid_node.simulation import Sim
from solid_node.simulation.run import Run
from tests.running_project.machine import (Curved, OpenGate, Ratchet, Smooth,
                                           Swept, Train, TrainBody, TwoStops,
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


def looped(label, sim, travel, ticks, input_id='steer'):
    """`ticks` iterations of restore + move + run, so a tick that RETIRES
    its command can be measured repeatedly."""
    taken = sim.snapshot()
    for _ in range(100):
        sim.restore(taken)
        handle = sim.move(input_id, by=travel, duration=sim.dt)
        sim.run(sim.dt)
    started = time.perf_counter()
    for _ in range(ticks):
        sim.restore(taken)
        sim.move(input_id, by=travel, duration=sim.dt)
        sim.run(sim.dt)
    elapsed = time.perf_counter() - started
    print(f'{label}: {elapsed:.3f} s for {ticks} iterations '
          f'= {elapsed / ticks * 1e3:.3f} ms/iteration   '
          f'-> {handle.status}')
    return elapsed / ticks


print('1. A tick with no stop pays what it pays today\n')

running = Sim(Train(), 0.1)
running.rate('crank', 1.0)
train = measure('running  Train    no ranged coordinate  ', running, TICKS)

untimed = Sim(TrainBody(), 0.1)
untimed.trigger('Park')
plain = measure('untimed  TrainBody                      ', untimed, TICKS)

smooth = Sim(Smooth(), 1 / 240)
smooth.rate('crank', 120.0)
measure('running  Smooth   no jump               ', smooth, TICKS)

quiet = Sim(Window(), 1 / 240)
quiet.rate('crank', 120.0)
measure('running  Window   no crossing           ', quiet, TICKS)

busy = Sim(Window(), 1 / 240)
busy.rate('crank', 360 * 240.0)
measure('running  Window   one crossing/tick     ', busy, TICKS)

# A RANGED machine that does not block: the number bound costs the
# comparison that was always there, the expression bound one graph
# evaluation per tick on top of it.
ranged = Sim(Swept(), 0.1)
ranged.rate('motor', 90.0)
measure('running  Swept    number bound, no stop  ', ranged, TICKS)

ratchet = Sim(Ratchet(), 0.1)
ratchet.rate('arbor', 1.0)
measure('running  Ratchet  EXPRESSION bound, no stop', ratchet, TICKS)

print(f'\nTrain / untimed TrainBody: {train / plain:.2f}x')
print('cycle 1 recorded 1.044 ms/tick and cycle 2 1.057 on this worktree.')

print('\n2. A blocking tick, against the same loop that does not block\n')

free = looped('Swept    affine chain, no stop      ',
              Sim(Swept(), 0.1), 4.0, 2_000)
stopped = looped('Swept    affine chain, STOPS       ',
                 Sim(Swept(), 0.1), 10.0, 2_000)
print(f'  blocking / free on the same machine: {stopped / free:.2f}x')

curved_free = looped('Curved   searched chain, no stop   ',
                     Sim(Curved(), 1.0), 20.0, 2_000, input_id='crank')
curved_stop = looped('Curved   searched chain, STOPS    ',
                     Sim(Curved(), 1.0), 40.0, 2_000, input_id='crank')
print(f'  blocking / free on the same machine: '
      f'{curved_stop / curved_free:.2f}x')


##############################################
# The same thing deterministically: what the engine ASKED FOR. Wall clock
# says what a machine did today; these counts are the same anywhere.


def counted(build, moves):
    """One tick of `build()` under `moves`, with the graph evaluations,
    the propagation passes and the CANDIDATE passes counted."""
    evaluations, passes, candidates = [], [], []
    original_evaluate = GraphValue.evaluate
    original_pass = Run._pass
    original_pushes = Run._pushes

    sim = build()
    for input_id, travel in moves:
        sim.move(input_id, by=travel, duration=sim.dt)
    sim.run(sim.dt)          # prime: compile, warm the caches
    sim.reset()

    GraphValue.evaluate = lambda self, inputs: (
        evaluations.append(1) or original_evaluate(self, inputs))
    Run._pass = lambda self, values, deltas, found, tick: (
        passes.append(1) or original_pass(self, values, deltas, found, tick))
    Run._pushes = lambda self, candidate, delta, key, values: (
        candidates.append(1)
        or original_pushes(self, candidate, delta, key, values))
    try:
        handles = [sim.move(input_id, by=travel, duration=sim.dt)
                   for input_id, travel in moves]
        sim.run(sim.dt)
    finally:
        GraphValue.evaluate = original_evaluate
        Run._pass = original_pass
        Run._pushes = original_pushes
    return (len(evaluations), len(passes), len(candidates),
            ', '.join(f'{handle.input} {handle.status}' for handle in handles))


print('\n3. One tick, deterministically\n')
for label, build, moves in (
        ('Train    no range  ', lambda: Sim(Train(), 0.1),
         [('crank', 1.0)]),
        ('Swept    no stop   ', lambda: Sim(Swept(), 0.1),
         [('steer', 4.0)]),
        ('Swept    STOPS     ', lambda: Sim(Swept(), 0.1),
         [('steer', 10.0)]),
        ('Ratchet  no stop   ', lambda: Sim(Ratchet(), 0.1),
         [('arbor', 4.0)]),
        ('Ratchet  STOPS     ', lambda: Sim(Ratchet(), 0.1),
         [('arbor', -10.0)]),
        ('Curved   no stop   ', lambda: Sim(Curved(), 1.0),
         [('crank', 20.0)]),
        ('Curved   STOPS     ', lambda: Sim(Curved(), 1.0),
         [('crank', 40.0)]),
        ('TwoStops TWO STOPS ', lambda: Sim(TwoStops(), 1.0),
         [('lever_in', 8.0), ('steer', 10.0)]),
        ('OpenGate STOPS     ', lambda: Sim(OpenGate(), 1.0),
         [('push', 10.0), ('crank', 30.0)])):
    graphs, passes, candidates, status = counted(build, moves)
    print(f'{label}: {graphs:4d} graph evaluations, {passes} propagation '
          f'pass(es), {candidates} candidate pass(es)   -> {status}')
