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

from solid_node.motion.ports import declared_time

from .driver import DriverState
from .enumeration import qualified_drivers, qualified_instructions
from .timebase import finite_seconds


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

    def __init__(self, node, dt, meshes=False, state=None, record=None):
        dt = finite_seconds(dt, 'dt')
        if dt <= 0:
            raise ValueError(f'dt must be greater than zero, not {dt!r}')
        self.node = node
        self.dt = dt
        self.tick = 0
        self._run = None
        # Enumerated across the WHOLE linked tree, not off the root
        # class: a machine's drivers live on its mechanisms, and a
        # machine whose root declares none would otherwise get an empty
        # bank and fail on its own first render. The bank is keyed by
        # the same qualified ids the serialized document publishes,
        # because both come from this one authority.
        self.drivers = {identifier: DriverState(identifier, declaration)
                        for identifier, declaration
                        in qualified_drivers(node).items()}
        # After the instruction walk, not before: `qualified_instructions`
        # is another `drive_tree`, and it rebinds every declared default
        # as it descends. The rest render below has to be the LAST thing
        # that poses the tree before the run reads its coordinates off it.
        self.instructions = qualified_instructions(node)
        self._trajectory = []
        self._at = {}
        self._every = []
        self._bind_initial(state)
        base = declared_time(type(node))
        if base is not None and base.mode == 'running':
            # The running engine and the compile step are imported HERE,
            # and nowhere else: a model that declares no running time
            # never loads either (capability `cli-startup-cost`). The
            # construction that follows is design.md section 4 -- the
            # untimed rest render above, the bank read off the tree, the
            # program compiled from what that render solved, the initial
            # snapshot, and then the run's own binding of the whole bank.
            from .run import Run

            self._run = Run(self, record)
        if meshes:
            node.assemble()
            node.build_stls()

    def _bind_initial(self, state):
        """Bind the declared defaults, overridden by `state=`, and render
        once: the untimed rest pose every simulation starts from.

        A name in `state` that is not a declared driver id is refused
        here rather than delivered: a joint coordinate id among them is
        refused too, because under a running root the initial
        coordinates come from the rest pose and nowhere else.
        """
        for identifier, value in (state or {}).items():
            try:
                self.drivers[identifier].value = value
            except KeyError:
                known = ', '.join(sorted(self.drivers)) or 'none'
                raise ValueError(
                    f"state={{'{identifier}': ...}} names no declared "
                    f'driver of {type(self.node).__name__}. An initial '
                    f'state names a driver by its qualified id -- a joint '
                    f"coordinate's initial value comes from the rest pose "
                    f'the declared drivers produce, never from here; '
                    f'declared: {known}.') from None
        self.node.set_state(**self._binding())

    @property
    def running(self):
        """Whether this simulation's root declares `Time.running()`, and
        the run therefore owns its coordinates."""
        return self._run is not None

    def _running(self, what):
        if self._run is None:
            raise TypeError(
                f'{what} belongs to a RUNNING simulation, and '
                f'{type(self.node).__name__} declares no time base or a '
                f'looping one. Declare time = Time.running() on the root '
                f'to have the simulation own its coordinates, retain their '
                f'history and take commands.')
        return self._run

    ##############################################
    # The running surface

    def move(self, input_id, by=None, to=None, duration=None):
        """Move a declared input BY a travel or TO a value, over
        `duration` seconds, and return the handle reporting what the run
        admits. A duration of zero -- or none -- settles at the current
        tick without advancing the clock."""
        return self._running('move()').move(input_id, by=by, to=to,
                                            duration=duration)

    def rate(self, input_id, rate):
        """Run a declared input at `rate` design units per simulated
        second until released with `rate(input, 0)`."""
        return self._running('rate()').rate(input_id, rate)

    @property
    def commands(self):
        """The handles of the commands currently owning an input."""
        return self._running('commands').commands

    @property
    def program(self):
        """The compiled program the run integrates."""
        return self._running('program').program

    @property
    def initial(self):
        """The snapshot taken at construction: the rest pose."""
        return self._running('initial').initial

    def snapshot(self):
        """This run's whole state as a value object."""
        return self._running('snapshot()').snapshot()

    def restore(self, snapshot):
        """Put this run back to `snapshot`, refusing one taken over a
        different program or a different `dt` before touching
        anything."""
        return self._running('restore()').restore(snapshot)

    def reset(self):
        """Restore the initial snapshot."""
        return self._running('reset()').reset()

    @property
    def state(self):
        """The current snapshot by qualified id: a fresh dict, so a
        caller holding one holds a value and not a view of the running
        simulation.

        Under a RUNNING root that is the run's whole bank -- every driver
        AND every joint coordinate of the linked tree -- because under
        that base the coordinates are the state. Under any other root it
        is the driver bank, exactly as it always was."""
        if self._run is not None:
            return self._run.state
        return {name: driver.value
                for name, driver in sorted(self.drivers.items())}

    @property
    def trajectory(self):
        """What was recorded, oldest first.

        Under a running root that is the bounded ring `record=` asked
        for, and `[]` when it asked for none; under any other root the
        list every tick is appended to, as before."""
        if self._run is not None:
            return self._run.trajectory
        return self._trajectory

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
        tick = self._ticks(t, 'instant')
        if tick < self.tick:
            raise ValueError(
                f'instant {t} is before current simulation time '
                f'{self.time} (tick {self.tick})')
        return _At(self, tick)

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
        if self._run is not None:
            # Under a running root an instruction is the run's own
            # command: `targets=` a move TO each target, `by=` a move BY
            # each travel, every input claimed before any of them starts.
            return self._run.trigger(path, instruction, name)
        ticks = self._ticks(instruction.duration,
                            f"duration of instruction '{name}'")
        for driver_name, amount in (instruction.targets
                                    or instruction.by).items():
            driver = self._driver('.'.join(path + (driver_name,)), name)
            native = driver.declaration.native(amount)
            if instruction.relative:
                # A relative instruction ramps from where the driver
                # stands, which is well defined over a driver bank under
                # every time base.
                native = driver.value + native
            driver.ramp_to(native, ticks, self.tick)
        if ticks == 0:
            # A zero-tick ramp is complete at the trigger instant. Rebind
            # once after every target has settled so the node sees one
            # complete, internally consistent snapshot.
            self.node.set_state(**self._binding())

    def run(self, duration):
        """Step for `duration` seconds of simulated time.

        Actions already due at the current tick run first, so a
        scenario opening with `at(0.0).trigger(...)` takes effect on
        the first tick rather than one tick late. Then each tick
        advances every program, binds the whole snapshot, records it,
        and only then runs what was scheduled -- an action must see the
        state its tick produced, never the one before it.
        """
        duration = finite_seconds(duration, 'duration')
        if duration < 0:
            raise ValueError(
                f'duration must be non-negative, not {duration!r}')
        end = self.tick + self._ticks(duration, 'duration')
        self._fire(self.tick)
        while self.tick < end:
            if self._run is not None:
                # One tick of design.md section 7: the increments the
                # active commands admit, propagated over the compiled
                # program, committed only once nothing refused them, and
                # bound as the run.
                self._run.advance()
            else:
                self.tick += 1
                states = {name: driver.advance(self.tick)
                          for name, driver in sorted(self.drivers.items())}
                self.node.set_state(**dict(states, time=self.time))
                self._trajectory.append((self.tick, states))
            self._fire(self.tick)
            for slot in self._every:
                if self.tick % slot.period_ticks == 0:
                    slot.run()

    def _fire(self, tick):
        for action in self._at.pop(tick, []):
            action(self)

    def _ticks(self, value, what):
        value = finite_seconds(value, what)
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
