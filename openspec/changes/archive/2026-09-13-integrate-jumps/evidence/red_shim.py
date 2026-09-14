# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A pytest plugin that installs the NAMES this cycle adds, and lifts
cycle 1's refusal, so every red of section 2 can be seen for its own
reason rather than as one collection error.

Run as `python -m pytest -p red_shim ...` with this directory on
PYTHONPATH. It exports `TooManyCrossings` and `Crossing`, gives `Edge` an
empty `plans` and `Sim` an empty `crossings`, and empties `_JUMP_CALLS`
and `_JUMP_OPERATORS` so a jump-carrying law COMPILES and is integrated
by cycle 1's own two evaluations -- the ABSOLUTE reading.

Nothing here partitions a tick, samples a branch, locates a crossing or
refuses one: every behavioural case below therefore fails on the number
the absolute reading gives (76 after two turns, 0 for a gate closing
mid-tick, nothing at all for a crowded tick), which is exactly the
reading this cycle replaces.

With `JUMPS_RED_LIFT=0` the refusal is KEPT, so every case instead shows
the red the unshimmed tree gives it: cycle 1 refusing the law by name.
Both runs are recorded, because a case whose two readings happen to
agree (a jump law continuous at its boundary, such as the fixture carry
with no lead) is red only in that second run.
"""

import os

import solid_node.simulation as simulation
import solid_node.simulation.program as program
from solid_node.motion.couplings import CouplingError


class TooManyCrossings(CouplingError):
    pass


class Crossing(tuple):
    pass


simulation.TooManyCrossings = TooManyCrossings
simulation.Crossing = Crossing

# Cycle 1 refused these by name. Emptying the two tuples lifts the
# refusal and nothing else: `_graph_of` goes on rejecting raw text and
# calls outside SYMBOLIC_BUILTINS, and `Edge.increments` goes on taking
# the difference of two evaluations of the whole law.
if os.environ.get('JUMPS_RED_LIFT', '1') != '0':
    program._JUMP_CALLS = ()
    program._JUMP_OPERATORS = ()

program.Edge.plans = ()


def _crossings(self):
    self._running('crossings')
    return []


simulation.sim.Sim.crossings = property(_crossings)
