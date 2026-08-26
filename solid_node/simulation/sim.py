# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The fixed-dt stepping loop.

One assembly, one step size, one integer tick counter. Everything a
scenario says in seconds is converted to a whole number of ticks the
moment it is said, and rejected there if it is not one: an instant
carried as an accumulating float would drift off the tick it names,
and no assertion scheduled on it would be reproducible. That is
ADR-050's integer-arithmetic reasoning applied to simulation time, and
it is what lets two runs of one scenario be compared with `==`.

Scheduled actions are deferred callables. The ADR sketched
`sim.at(2.5).assertEqual(sim.state['x'], 0)`, which cannot work --
Python evaluates the arguments when the line is registered, so the
assertion would read the state at t=0 and pass or fail for the wrong
instant (spike/FINDINGS.md seam 3). `at(t).run(fn)` hands `fn` the
simulation instead, at the tick it was scheduled for.

Cadence exists because of the cost asymmetry the spike measured: a
bare tick is microseconds while one mesh assertion is milliseconds, so
continuous checking is dominated entirely by the assertions. Ticks are
free; cadence budgets assertion cost. Each slot accounts its own calls
and seconds so a scenario report can say that separately from the cost
of stepping.
"""

import time
from collections import namedtuple

from .driver import DriverState
from .enumeration import qualified_drivers, qualified_instructions


CadenceCost = namedtuple('CadenceCost', 'period_ticks calls seconds')


class _Cadence:
    """One `every()` slot and the cost it has run up so far."""

    __slots__ = ('period_ticks', 'fn', 'args', 'calls', 'seconds')

    def __init__(self, period_ticks, fn, args):
        self.period_ticks = period_ticks
        self.fn = fn
        self.args = args
        self.calls = 0
        self.seconds = 0.0

    def run(self):
        started = time.perf_counter()
        try:
            self.fn(*self.args)
        finally:
            # Accounted even when the action raises: the run stops
            # there, and a scenario report of a failed run should still
            # be able to say what its assertions cost.
            self.seconds += time.perf_counter() - started
            self.calls += 1


class _At:
    """The registrar `at(t)` returns: what to do at one tick.

    A separate object rather than `at(t, action)` so the scenario reads
    as the instant first and the intent second, and so the intent is
    always something to CALL later.
    """

    def __init__(self, sim, tick):
        self._sim = sim
        self._tick = tick

    def trigger(self, name):
        """Trigger the named instruction at this instant."""
        self._add(lambda sim: sim.trigger(name))

    def run(self, fn):
        """Call `fn(sim)` at this instant, after the tick has bound its
        snapshot."""
        self._add(fn)

    def _add(self, action):
        self._sim._at.setdefault(self._tick, []).append(action)


class Sim:
    """A stepped simulation over one assembly at a fixed `dt`.

    Construction enumerates every driver in the node's LINKED TREE and
    binds each one's default through `set_state` by qualified id, so an
    assembly whose render() reads a driver -- including one whose
    drivers live only on its children -- is rendered under a complete
    snapshot from the very first render rather than failing on an
    unbound entry. That is the resolution stage 1 deferred to this
    layer: the framework invents no defaults, the declarations state
    them.

    The bank, the trajectory, the programs and instruction targets all
    key by that same qualified id, so two instances of one mechanism
    step independently and the id a scenario writes is the id the
    serialized document publishes.

    `meshes=True` additionally assembles the node and builds its STLs,
    which is what a scenario asserting on geometry needs and what a
    scenario asserting on state should not pay for. Per-tick re-renders
    never touch the artifact path, so this happens once, here.
    """

    def __init__(self, node, dt, meshes=False):
        self.node = node
        self.dt = dt
        self.tick = 0
        # Enumerated across the WHOLE linked tree, not off the root
        # class: a machine's drivers live on its mechanisms, and a
        # machine whose root declares none would otherwise get an empty
        # bank and fail on its own first render. The bank is keyed by
        # the same qualified ids the serialized document publishes,
        # because both come from this one authority.
        self.drivers = {identifier: DriverState(identifier, declaration)
                        for identifier, declaration
                        in qualified_drivers(node).items()}
        self.instructions = qualified_instructions(node)
        self.trajectory = []
        self._at = {}
        self._every = []
        node.set_state(**self._binding())
        if meshes:
            node.assemble()
            node.build_stls()

    @property
    def state(self):
        """The current snapshot by qualified driver id: a fresh dict, so
        a caller holding one holds a value and not a view of the running
        simulation."""
        return {name: driver.value
                for name, driver in sorted(self.drivers.items())}

    @property
    def time(self):
        """The exact instant this simulation stands at, in seconds.

        Computed from the integer tick count on every access, never
        accumulated: `k*dt` is a fixed point, and a float advanced by
        `+= dt` drifts off the instant a scenario names (ADR-050's
        reasoning applied to simulation time).
        """
        return self.tick * self.dt

    def _binding(self):
        """The full snapshot as `set_state` takes it: every driver by
        qualified id, plus the one global entry.

        `time` is a driver like the rest, and under a simulation it is
        this clock in SECONDS -- a machine executing instructions has no
        period to normalize against, so the 0..1 `$t` timeline ADR-008
        provides is the wrong thing to bind here. Outside a simulation
        that path is untouched.
        """
        return dict(self.state, time=self.time)

    @property
    def cadence_costs(self):
        """What each cadence slot has cost so far, in declaration
        order: a scenario report states assertion cost per slot."""
        return tuple(CadenceCost(slot.period_ticks, slot.calls, slot.seconds)
                     for slot in self._every)

    @property
    def assertion_stats(self):
        """(calls, mean seconds per call) across every cadence slot."""
        calls = sum(slot.calls for slot in self._every)
        seconds = sum(slot.seconds for slot in self._every)
        return calls, (seconds / calls if calls else 0.0)

    def at(self, t):
        """The registrar for instant `t`, in seconds."""
        return _At(self, self._ticks(t, 'instant'))

    def every(self, period, fn, *args):
        """Call `fn(*args)` every `period` seconds of simulated time.

        The arguments are bound now and the call deferred, which is
        exactly right for an assertion whose subject is a node: the
        node is the same object at every tick, and what changes is the
        snapshot bound into it.
        """
        ticks = self._ticks(period, 'period')
        if ticks < 1:
            # A cadence of no ticks is the one thing this cannot mean:
            # "every tick" is period == dt, and the loop would divide
            # by zero rather than say so.
            raise ValueError(
                f'period {period} is shorter than one dt={self.dt} tick')
        self._every.append(_Cadence(ticks, fn, args))

    def trigger(self, name):
        """Start the named instruction's ramps at the current tick.

        `name` is qualified the same way a driver id is: an instruction
        declared on a child is `x_axis.Home`, one declared on the root
        keeps its bare name. Its targets are class-local, so they
        resolve against the declaring node's own path -- which is what
        makes "home the X axis" home only the X axis.
        """
        path, instruction = self._instruction(name)
        ticks = self._ticks(instruction.duration,
                            f"duration of instruction '{name}'")
        for driver_name, target in instruction.targets.items():
            driver = self._driver('.'.join(path + (driver_name,)), name)
            driver.ramp_to(driver.declaration.native(target), ticks, self.tick)

    def run(self, duration):
        """Step for `duration` seconds of simulated time.

        Actions already due at the current tick run first, so a
        scenario opening with `at(0.0).trigger(...)` takes effect on
        the first tick rather than one tick late. Then each tick
        advances every program, binds the whole snapshot, records it,
        and only then runs what was scheduled -- an action must see the
        state its tick produced, never the one before it.
        """
        end = self.tick + self._ticks(duration, 'duration')
        self._fire(self.tick)
        while self.tick < end:
            self.tick += 1
            states = {name: driver.advance(self.tick)
                      for name, driver in sorted(self.drivers.items())}
            self.node.set_state(**dict(states, time=self.time))
            self.trajectory.append((self.tick, states))
            self._fire(self.tick)
            for slot in self._every:
                if self.tick % slot.period_ticks == 0:
                    slot.run()

    def _fire(self, tick):
        for action in self._at.pop(tick, []):
            action(self)

    def _ticks(self, value, what):
        count = round(value / self.dt)
        if abs(count * self.dt - value) > 1e-9:
            raise ValueError(
                f'{what} {value} is not a whole number of dt={self.dt} ticks')
        return count

    def _instruction(self, name):
        try:
            _, path, instruction = self.instructions[name]
        except KeyError:
            known = ', '.join(sorted(self.instructions)) or 'none'
            raise KeyError(f"no instruction '{name}' declared anywhere in "
                           f'{type(self.node).__name__}; declared: '
                           f'{known}') from None
        return path, instruction

    def _driver(self, name, instruction_name):
        try:
            return self.drivers[name]
        except KeyError:
            known = ', '.join(sorted(self.drivers)) or 'none'
            raise KeyError(f"instruction '{instruction_name}' targets driver "
                           f"'{name}', which nothing in "
                           f'{type(self.node).__name__} declares; declared: '
                           f'{known}') from None
