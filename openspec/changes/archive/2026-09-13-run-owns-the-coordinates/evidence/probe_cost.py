"""Task 5.1: what one tick of a running simulation costs, beside what
one tick of the untimed stepping loop costs on the same machine.

The number cycle 4's compiled evaluator is measured against. The engine
here is `GraphValue.evaluate` per edge per tick, which builds a dict and
walks the graph twice, and one `set_state` per tick, which is a full
delivery walk plus one enumeration -- the cost every tick already paid
for drivers.
"""

import time
import tracemalloc

from solid_node.simulation import Sim
from tests.running_project.machine import Train, TrainBody

TICKS = 10_000
DT = 0.1


def measure(label, sim, seconds, prime=1.0):
    sim.run(prime)
    tracemalloc.start()
    started = time.perf_counter()
    sim.run(seconds)
    elapsed = time.perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    ticks = round(seconds / sim.dt)
    print(f'{label}: {elapsed:.3f} s for {ticks} ticks '
          f'= {elapsed / ticks * 1e3:.3f} ms/tick, '
          f'tracemalloc peak {peak / 1024:.1f} KiB, '
          f'trajectory {len(sim.trajectory)} entries')
    return elapsed / ticks


running = Sim(Train(), DT)
running.rate('crank', 1.0)
run_cost = measure('running  Train   (record=None)', running, TICKS * DT)

ringed = Sim(Train(), DT, record=64)
ringed.rate('crank', 1.0)
measure('running  Train   (record=64) ', ringed, TICKS * DT)

untimed = Sim(TrainBody(), DT)
untimed.trigger('Park')
untimed_cost = measure('untimed  TrainBody           ', untimed, TICKS * DT)

print(f'ratio running/untimed per tick: {run_cost / untimed_cost:.2f}x')
