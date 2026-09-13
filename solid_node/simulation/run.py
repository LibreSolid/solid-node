# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The run: what owns a running root's coordinates, and what advances
them.

A pose used to be a function of the current input values and nothing
else, which is exactly the history a machine has: a Curta pinion posed at
any crank angle is right, and turned through two crank revolutions is
wrong, because a law can only say where the pinion IS for a crank angle,
never where it WAS. Under `time = Time.running()` the simulation
therefore owns a BANK -- every driver and every joint coordinate of the
linked tree, by qualified id -- initialized from the untimed rest pose
and advanced by INCREMENTS.

Three things make that safe next to a solver built to do the opposite.

The run binds through `set_state`, so `render()` and `simulate()` stay
pure functions of the bound snapshot: an inspection, an extra render or
an extra binding of the same snapshot advances nothing. It binds as a
`RunBinder`, which the solver recognizes -- the freshness clear leaves
its slots alone, and a relation whose driven ends it owns is recorded as
solved BY THE RUN rather than refused as doubly bound. And the run
binder wraps the DELIVERY of `set_state` alone, never the enumeration
that follows: a plain port an author's `simulate()` binds keeps the
author as its binder, is cleared and rebound every tick, and follows the
run-owned coordinate it reads.

There is no memory bank and the author declares no state. What a
coordinate remembers is where it stands.
"""

import math
from collections import deque
from dataclasses import dataclass, field, replace

from solid_node.motion.ports import RunBinder, get_coordinate

from .driver import RampProgram
from .program import (compile_program, qualified_coordinates, Stop,
                      TooManyCrossings, UnsupportedLaw,
                      _BISECTION_ROUNDS, _CROSSING_TOLERANCE, _SUBDIVISIONS)


# Two increments agree when they are within this of each other,
# relatively: the tick's arithmetic is a difference of two evaluations,
# so two routes to one coordinate differ in the last bits rather than
# not at all.
_TOLERANCE = 1e-9


class RunConflict(ValueError):
    """Two increments disagreed on one coordinate over one tick. The
    tick committed nothing."""


class StopInvariantError(RuntimeError):
    """A coordinate left a declared bound over a tick and locating the
    stop stopped no input that was moving.

    Every stop stops at least one moving input -- a coordinate that left
    its bound was moved by something, and everything that moves it is in
    its group -- so this is a broken invariant of the run rather than a
    dt that is too coarse. The tick committed nothing.
    """


def _agree(left, right):
    return abs(left - right) <= _TOLERANCE * max(1.0, abs(left), abs(right))


def _design(declaration, native):
    """`native` driver state back in the DESIGN units a caller states a
    move in -- the inverse of `Driver.native`."""
    if declaration.scale is None:
        return native
    return native * declaration.scale


##############################################
# Commands


class Command:
    """The handle a `move` or a `rate` returns, and goes on reporting
    after the run has retired it.

    `requested` and `admitted` are in the input's DESIGN units -- the
    units an instruction target is stated in -- while the bank stays
    native. `status` is one of `active`, `completed`, `blocked`,
    `refused` and `cancelled`. `blocked` is the one a command whose input
    was STOPPED retires with: the tick happened and the machine would not
    go further, so `admitted` is the travel it actually made -- every
    completed tick's travel plus the fraction of the stopping tick's it
    made before the stop -- and nothing anywhere remembers the rest.
    """

    __slots__ = ('input', 'kind', 'status', 'declaration', 'native',
                 'native_rate', 'ticks', 'started', 'admitted_native',
                 '_program')

    def __init__(self, input_id, kind, declaration, started,
                 native=None, native_rate=None, ticks=None, value=None):
        self.input = input_id
        self.kind = kind
        self.declaration = declaration
        self.status = 'active'
        self.native = native
        self.native_rate = native_rate
        self.ticks = ticks
        self.started = started
        self.admitted_native = 0
        self._program = (
            RampProgram(value, value + native, ticks, declaration.dtype)
            if kind == 'move' and ticks else None)

    ##############################################
    # What the caller reads

    @property
    def requested(self):
        """The travel asked for, in design units -- `None` for a rate,
        which states a speed and no total."""
        if self.kind == 'rate':
            return None
        return _design(self.declaration, self.native)

    @property
    def admitted(self):
        """The travel actually admitted so far, in design units."""
        return _design(self.declaration, self.admitted_native)

    @property
    def remaining(self):
        if self.kind == 'rate':
            return None
        return self.requested - self.admitted

    @property
    def rate(self):
        """A rate's speed in design units per simulated second."""
        if self.kind != 'rate':
            return None
        return _design(self.declaration, self.native_rate)

    def cancel(self):
        """Stop this command where it stands. A command already retired
        keeps whatever it reported."""
        if self.status == 'active':
            self.status = 'cancelled'
        return self

    def __repr__(self):
        return (f'<{self.kind} {self.input} {self.status}: '
                f'{self.admitted} admitted>')

    ##############################################
    # What the run reads

    def admits(self, tick, dt):
        """How far this command moves its input over the tick ENDING at
        `tick` -- a pure function of the tick count since it started, so
        a replayed run admits exactly the same travel."""
        elapsed = tick - self.started
        if elapsed < 0:
            return 0
        if self.kind == 'rate':
            return (self._cumulative(elapsed, dt)
                    - self._cumulative(elapsed - 1, dt))
        if not self.ticks:
            # A zero-duration move lands entirely at the tick it was
            # requested on, and nothing after it.
            return self.native if elapsed == 0 else 0
        if elapsed == 0 or elapsed > self.ticks:
            return 0
        return (self._program.value_at(elapsed)
                - self._program.value_at(elapsed - 1))

    def _cumulative(self, elapsed, dt):
        if elapsed <= 0:
            return 0
        travelled = self.native_rate * dt * elapsed
        # TRUNCATED toward zero, so a negative rate rounds the way a
        # positive one does: floor would make the state LEAD the ideal
        # by up to one native unit where a positive rate LAGS it.
        return math.trunc(travelled) if self.declaration.dtype is int \
            else travelled

    def finished(self, tick):
        if self.kind == 'rate':
            return False
        return tick - self.started >= (self.ticks or 0)

    def record(self):
        """This command frozen into a snapshot entry."""
        return (self.input, self.kind, self.native, self.native_rate,
                self.ticks, self.started, self.admitted_native, self.status)


##############################################
# The snapshot


@dataclass(frozen=True)
class RunSnapshot:
    """A running simulation's whole state, as a value.

    Carries the compiled program's IDENTITY rather than the program, so
    a snapshot can be compared without holding a tree alive, and so
    restoring it into a machine whose kinematics have moved on is
    refused rather than silently wrong.
    """

    program: str
    dt: float
    tick: int
    bank: tuple = field(default=())
    commands: tuple = field(default=())

    def __repr__(self):
        return (f'<run snapshot at tick {self.tick}, '
                f'{len(self.bank)} coordinates>')


##############################################
# The run


class Run:
    """What owns a running root's coordinates for one `Sim`."""

    def __init__(self, sim, record=None):
        self.sim = sim
        self.node = sim.node
        self.dt = sim.dt
        self.binder = RunBinder()
        self.ring = _ring(record)
        # A second ring of the same length, for the CROSSINGS located
        # inside a tick, and a THIRD for the STOPS. `record=None` builds
        # none of them, so a run that records nothing pays nothing for
        # the record.
        self.crossing_ring = _ring(record)
        self.stop_ring = _ring(record)
        self.active = {}

        inputs = {identifier: state.declaration
                  for identifier, state in sim.drivers.items()}
        coordinates = qualified_coordinates(sim.node)
        clash = sorted(set(inputs) & set(coordinates))
        if clash:
            raise ValueError(
                f'{", ".join(clash)} is claimed twice under a running root: '
                f'a driver and a joint coordinate cannot share a qualified '
                f'id, because the run banks both under it. Rename one.')

        self.coordinates = coordinates
        self.bank = dict(_driver_values(sim))
        unbound = []
        for identifier, (node, name) in sorted(coordinates.items()):
            value = get_coordinate(node, name)._value
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                unbound.append(identifier)
            else:
                self.bank[identifier] = value
        if unbound:
            raise ValueError(
                f'the rest render leaves '
                f'{", ".join(unbound)} unbound. A running simulation owns '
                f'every joint coordinate of the tree and needs a rest value '
                f'for each, because what a coordinate remembers is where it '
                f'stands: drive it with a relation, or bind it in '
                f'simulate() under a guard that finds it unbound.')

        self.program = compile_program(sim.node, inputs, coordinates)
        self.keys = {identifier: ('input', identifier) for identifier in inputs}
        for identifier, (node, name) in coordinates.items():
            self.keys[identifier] = ('slot', id(get_coordinate(node, name)))
        self.bank_keys = set(self.keys.values())
        self.spans = self.program.spans

        self.initial = self.snapshot()
        # From here the run OWNS the coordinates: `set_state` binds every
        # coordinate entry as this run, the solver leaves them alone, and
        # an author's simulate() that binds one is refused as doubly
        # bound -- at construction, where the message can name the class.
        self.node.__dict__['_run_binder'] = self.binder
        self.bind()

    ##############################################
    # What the Sim delegates

    @property
    def state(self):
        return dict(sorted(self.bank.items()))

    @property
    def commands(self):
        return tuple(self.active.values())

    @property
    def trajectory(self):
        return [] if self.ring is None else list(self.ring)

    @property
    def crossings(self):
        return [] if self.crossing_ring is None else list(self.crossing_ring)

    @property
    def stops(self):
        return [] if self.stop_ring is None else list(self.stop_ring)

    def bind(self):
        """Bind the whole bank, and the instant, to the tree.

        One `set_state`: its DELIVERY binds every coordinate entry under
        this run, and the ONE enumeration it runs afterwards happens with
        no run binder active, so an author's plain port keeps the author
        as its binder and is cleared and rebound like any other
        (design.md sections 4.5 and 7.7).
        """
        self.node.set_state(**dict(self.bank, time=self.sim.time))

    ##############################################
    # Requests

    def move(self, input_id, by=None, to=None, duration=None):
        declaration = self._input(input_id)
        if (by is None) == (to is None):
            raise ValueError(
                f"move('{input_id}', ...) states exactly one of by= (how "
                f'far to travel) and to= (where to land), both in design '
                f'units; got by={by!r} and to={to!r}.')
        value = self.bank[input_id]
        if to is not None:
            native = declaration.native(to) - value
        else:
            native = declaration.native(by)
        # A REVERSE request -- a negative `by`, a `to` below the
        # committed value -- is an ordinary one: it meets a declared
        # range as a physical stop exactly as a forward request does.
        ticks = self.sim._ticks(
            0.0 if duration is None else duration,
            f"duration of the move on '{input_id}'")
        self._claim(input_id)
        command = Command(input_id, 'move', declaration, self.sim.tick,
                          native=native, ticks=ticks, value=value)
        self.active[input_id] = command
        if not ticks:
            # A zero-duration move settles at the CURRENT tick, without
            # advancing the clock -- the rule ADR-083 states for a
            # zero-duration instruction.
            self.integrate(self.sim.tick, advance=False, only=command)
        return command

    def rate(self, input_id, rate):
        declaration = self._input(input_id)
        if rate == 0:
            running = self.active.get(input_id)
            if running is None or running.kind != 'rate':
                return None
            running.status = 'completed'
            del self.active[input_id]
            return running
        self._claim(input_id)
        native_rate = (rate if declaration.scale is None
                       else rate / declaration.scale)
        command = Command(input_id, 'rate', declaration, self.sim.tick,
                          native_rate=native_rate)
        self.active[input_id] = command
        return command

    def trigger(self, path, instruction, name):
        """An instruction under a running root: its targets as moves TO,
        its travels as moves BY -- every input claimed before any command
        starts, so an ownership conflict refuses the whole instruction
        and leaves nothing running."""
        stated = instruction.targets or instruction.by
        inputs = {driver_name: '.'.join(path + (driver_name,))
                  for driver_name in stated}
        for driver_name, input_id in inputs.items():
            self.sim._driver(input_id, name)
            self._claim(input_id)
        issued = []
        for driver_name, amount in stated.items():
            input_id = inputs[driver_name]
            if instruction.relative:
                issued.append(self.move(input_id, by=amount,
                                        duration=instruction.duration))
            else:
                issued.append(self.move(input_id, to=amount,
                                        duration=instruction.duration))
        return tuple(issued)

    def _claim(self, input_id):
        owner = self.active.get(input_id)
        if owner is not None:
            raise ValueError(
                f"'{input_id}' is already owned by {owner!r}. An input has "
                f'one owner at a time: cancel that command, or release the '
                f'rate with rate(input, 0), before asking for another.')

    def _input(self, input_id):
        state = self.sim.drivers.get(input_id)
        if state is None:
            known = ', '.join(sorted(self.sim.drivers)) or 'none'
            raise ValueError(
                f"'{input_id}' is not a declared input of "
                f'{type(self.node).__name__}. Only a declared driver can be '
                f'moved -- a joint coordinate is what a relation moves, not '
                f'what a command does; the declared inputs are: {known}.')
        return state.declaration

    ##############################################
    # The tick

    def advance(self):
        """One tick, and the clock with it."""
        self.integrate(self.sim.tick + 1, advance=True)

    def integrate(self, tick, advance, only=None):
        """One tick, in SEGMENTS.

        The tick's path is integrated by exactly one pass of cycles 1 and
        2 (`_pass`) over the whole stretch. If that would take a banked
        joint coordinate outside a declared bound, and FURTHER outside
        than it stood at the stretch's start, the bound is a physical
        stop: the fraction `t*` at which the coordinate reaches it is
        located, the stretch is re-integrated over `[0, t*]` only, the
        coordinate is committed AT its bound, every input whose movement
        pushes it is stopped for the rest of the tick, and what remains
        is examined again. The earliest `t*` is always taken first.

        The tick stays ATOMIC across its segments: the bank, the
        commands' admitted travel and the three records are STAGED and
        applied only when every segment has succeeded. A conflict, a
        `TooManyCrossings` or an unintegrable law in ANY segment commits
        nothing, exactly as an unsegmented tick does. Nothing is bound
        until the commit, so a refused tick touches no slot.
        """
        admissions = {}
        for input_id, command in self.active.items():
            if only is not None and command is not only:
                admissions[input_id] = 0
                continue
            admissions[input_id] = command.admits(tick, self.dt)
        moved = [self.active[input_id] for input_id, delta
                 in admissions.items() if delta]

        # Each bound as a number for THIS tick, from the committed bank,
        # before any segment: every segment of one tick is measured
        # against the same number.
        bounds = self._bounds()
        staged = self.bank
        admitted = {input_id: 0 for input_id in admissions}
        stopped = set()
        # Fresh lists per tick, appended to the rings only on COMMIT, so
        # a refused tick records nothing.
        crossings = None if self.crossing_ring is None else []
        stops = None if self.stop_ring is None else []
        # Every stop event stops at least one input that was moving, and
        # a stopped input stays stopped, so a tick has at most as many
        # events as it has inputs admitting travel.
        limit = sum(1 for delta in admissions.values() if delta)
        start = 0.0
        events = 0

        try:
            while True:
                stretch = 1.0 - start
                scaled = self._scaled(admissions, stopped, stretch)
                values = self._values(staged)
                deltas = self._deltas(scaled)
                found = None if crossings is None else []
                self._pass(values, deltas, found, tick)
                committed = {
                    identifier: value + deltas.get(self.keys[identifier], 0.0)
                    for identifier, value in staged.items()}
                reached = self._reached(staged, committed, bounds)
                if not reached:
                    _record(crossings, found, start, 1.0)
                    staged = committed
                    for input_id, delta in scaled.items():
                        admitted[input_id] += delta
                    break

                events += 1
                if events > limit:
                    raise StopInvariantError(self._runaway(reached, limit))
                event = self._event(reached, staged, values, deltas)
                where = event[0][0]
                boundary = start + where * stretch

                segment = {input_id: delta * where
                           for input_id, delta in scaled.items()}
                deltas = self._deltas(segment)
                found = None if crossings is None else []
                self._pass(values, deltas, found, tick)
                committed = {
                    identifier: value + deltas.get(self.keys[identifier], 0.0)
                    for identifier, value in staged.items()}

                blocked = set()
                for _where, identifier, side, bound in event:
                    # AT the bound, exactly. The localization's own error
                    # is absorbed here rather than left for `set_state`
                    # to raise on, and the group's other coordinates
                    # stand within the tolerance the run already calls
                    # agreement.
                    committed[identifier] = bound
                    group = self._group(identifier, scaled, values)
                    blocked.update(group)
                    if stops is not None:
                        stops.append(Stop(tick, identifier, side, bound,
                                          boundary, tuple(sorted(group))))
                if not blocked:
                    raise StopInvariantError(self._runaway(reached, limit))

                _record(crossings, found, start, boundary)
                staged = committed
                for input_id, delta in segment.items():
                    admitted[input_id] += delta
                stopped |= blocked
                start = boundary
        except (RunConflict, TooManyCrossings, UnsupportedLaw,
                StopInvariantError):
            # A tick that fails commits nothing, every segment of it
            # included.
            self._refuse(moved)
            raise

        # Nothing above bound anything. From here the tick is taken.
        self.bank = staged
        if advance:
            self.sim.tick = tick
        for input_id, delta in admitted.items():
            self.active[input_id].admitted_native += delta
        self._block(stopped)
        for input_id, command in list(self.active.items()):
            if only is not None and command is not only:
                # A zero-duration move is one EXTRA pass at the current
                # tick: it must not retire a command whose own tick has
                # not been admitted in it.
                continue
            if command.finished(tick):
                command.status = 'completed'
                del self.active[input_id]
        self.bind()
        if self.ring is not None:
            self.ring.append((self.sim.tick, dict(self.bank)))
            self.crossing_ring.extend(crossings)
            self.stop_ring.extend(stops)

    def _pass(self, values, deltas, found, tick):
        """ONE propagation over the compiled program: the whole of cycles
        1 and 2's tick, unchanged, over whatever stretch `deltas`
        describes.

        Mutates and returns `deltas`. Raises rather than retiring
        anything: what a failed segment does to the tick is the caller's
        business, because a segment is not a tick.
        """
        determined = set()
        for edge in self.program.edges:
            if edge.kind == 'check':
                predicted = edge.predicts(deltas, constant=0.0)
                received = deltas[edge.slot_key]
                if not _agree(predicted, received):
                    raise RunConflict(self._conflict(
                        edge, predicted, received))
                continue
            for key, delta in edge.increments(values, deltas, found, tick):
                if key in determined and not _agree(deltas[key], delta):
                    raise RunConflict(self._disagreement(edge, key, delta))
                deltas[key] = delta
                determined.add(key)
        return deltas

    def _scaled(self, admissions, stopped, stretch):
        """Each input's admission over one stretch: nothing for a stopped
        input, and the tick's own admission UNTOUCHED over a full
        stretch, so an unsegmented tick is the arithmetic it always
        was."""
        found = {}
        for input_id, delta in admissions.items():
            if input_id in stopped:
                found[input_id] = 0
            elif stretch == 1.0:
                found[input_id] = delta
            else:
                found[input_id] = delta * stretch
        return found

    def _deltas(self, admissions):
        deltas = {key: 0.0 for key in self.program.nodes}
        for input_id, delta in admissions.items():
            if delta:
                deltas[self.keys[input_id]] = delta
        return deltas

    ##############################################
    # Stops

    def _reached(self, held, committed, bounds):
        """Every banked coordinate that ends the stretch OUTSIDE a bound
        and FURTHER outside than it began it.

        This is cycle 1's `_check_spans` become a DETECTION: the same
        inclusive comparison, by the same committed value, costing the
        same one comparison per ranged coordinate on a tick that does not
        block. A coordinate already at or below its low bound that moves
        UP is free, and one that does not move at all is free, which is
        why a frozen coordinate standing on its bound raises nothing and
        divides by nothing.
        """
        found = []
        for identifier, low, high, _unit in bounds:
            value = committed[identifier]
            was = held[identifier]
            if low is not None and value < low and value < was:
                found.append((identifier, 'low', low))
            elif high is not None and value > high and value > was:
                found.append((identifier, 'high', high))
        return found

    def _event(self, reached, held, values, deltas):
        """The EARLIEST stop of this stretch, with everything within the
        crossing tolerance of it: one event, one segment boundary, the
        union of their groups, whether they are on one group or two.

        Ties are therefore never resolved by ordering; there is no
        ordering to get wrong.
        """
        located = sorted(
            (self._locate(identifier, side, bound, held, values, deltas),
             identifier, side, bound)
            for identifier, side, bound in reached)
        first = located[0][0]
        return [entry for entry in located
                if entry[0] - first <= _CROSSING_TOLERANCE]

    def _locate(self, identifier, side, bound, held, values, deltas):
        """The smallest fraction of the STRETCH at which `identifier`
        reaches `bound`, by design.md section 2's three cases.

        The coordinate's value along the path is `v(0)` plus the
        increment its DETERMINER EDGE gives over the path truncated at
        `t` -- which is the edge's own `increments` with every source
        delta multiplied by `t`, so a law that jumps contributes its
        subtracted-jump increment here too.
        """
        key = self.keys[identifier]
        edge = self.program.determiner.get(key)
        if edge is None:
            # A coordinate no edge determines cannot move, so it cannot
            # have left its span.
            raise StopInvariantError(
                f'{identifier} left its declared range over this tick and '
                f'no relation determines it, so nothing can have moved '
                f'it. The tick committed nothing.')
        index = edge.gives.index(key)
        value = held[identifier]
        if (bound - value) * (1.0 if side == 'high' else -1.0) <= 0.0:
            # Already at or beyond it: the stop is at the very start of
            # the stretch, and the coordinate stands where it stands.
            return 0.0
        if edge.affine[index]:
            cuts = edge.cuts(values, deltas, index)
            if not cuts:
                # Linear in `t`: one division, exact, no extra
                # evaluation. This is the ratchet, the rack, every wiring
                # edge and every derived coordinate's linear formula.
                travel = deltas[key]
                return _clamped((bound - value) / travel) if travel else 0.0
            return self._piecewise(edge, key, bound, value, values, deltas,
                                   cuts)
        return self._searched(edge, key, bound, value, values, deltas)

    def _piecewise(self, edge, key, bound, value, values, deltas, cuts):
        """An affine skeleton with a jump plan: piecewise affine in `t`,
        with breakpoints at the plan's own cuts, solved linearly inside
        the piece that brackets the bound. Exact."""
        left, below = 0.0, value
        for cut in cuts[1:]:
            here = value + self._along(edge, key, values, deltas, cut)
            if min(below, here) <= bound <= max(below, here):
                if here == below:
                    return left
                return left + (cut - left) * (bound - below) / (here - below)
            left, below = cut, here
        return 1.0

    def _searched(self, edge, key, bound, value, values, deltas):
        """Anything else: sampled at `_SUBDIVISIONS` points, bracketed
        and bisected to `_CROSSING_TOLERANCE` in at most
        `_BISECTION_ROUNDS` rounds -- the same three tolerances, the same
        shape and the same documented limit as a searched jump
        crossing."""
        points = [step / _SUBDIVISIONS for step in range(_SUBDIVISIONS + 1)]
        levels = [value + self._along(edge, key, values, deltas, where) - bound
                  for where in points]
        for step in range(_SUBDIVISIONS):
            below, above = levels[step], levels[step + 1]
            if below == 0.0:
                return points[step]
            if above == 0.0:
                return points[step + 1]
            if (below < 0.0) == (above < 0.0):
                continue
            low, high = points[step], points[step + 1]
            for _round in range(_BISECTION_ROUNDS):
                if high - low <= _CROSSING_TOLERANCE:
                    break
                middle = (low + high) / 2.0
                here = value + self._along(
                    edge, key, values, deltas, middle) - bound
                if here == 0.0 or (here < 0.0) != (below < 0.0):
                    high = middle
                else:
                    low, below = middle, here
            return (low + high) / 2.0
        return 1.0

    def _along(self, edge, key, values, deltas, t):
        """The increment `key` receives over the stretch truncated at
        `t`: one edge evaluation for a continuous law, one jump-plan
        partition-and-sum for a law that jumps."""
        truncated = {other: delta * t for other, delta in deltas.items()}
        return dict(edge.increments(values, truncated))[key]

    def _group(self, identifier, admissions, values):
        """The inputs a stop on `identifier` stops: the candidates the
        compiled program says reach it, filtered by whether their own
        movement over this stretch actually PUSHES it.

        Everything those inputs alone determine follows without any
        computation at all: their admissions are set to ZERO for the rest
        of the tick, and the ordinary propagation does the rest.
        """
        key = self.keys[identifier]
        found = []
        for candidate in sorted(self.program.sources.get(key, ())):
            delta = admissions.get(candidate, 0)
            if delta and self._pushes(candidate, delta, key, values):
                found.append(candidate)
        return found

    def _pushes(self, candidate, delta, key, values):
        """Whether `candidate`'s own admission, with every other input's
        set to zero, gives `key` a nonzero increment.

        One propagation over the edges between the two, on a blocking
        tick only. An input coupled to `key` only through a law that is
        currently disengaged -- an open clutch, a carry outside its
        window -- contributes nothing and is not stopped.
        """
        deltas = self._deltas({candidate: delta})
        for edge in self.program.edges:
            if edge.kind == 'check':
                continue
            if any(deltas[need] for need in edge.needs):
                for gives, increment in edge.increments(values, deltas):
                    deltas[gives] = increment
            if key in edge.gives:
                break
        return deltas[key] != 0.0

    def _block(self, stopped):
        """Every active command whose input is in the stopped group is
        retired reporting `blocked`, with the travel it actually
        admitted, and its input released so a new command may be issued
        at once.

        The same retirement `refused` performs, with a different word and
        a different meaning: `refused` says the tick did not happen,
        `blocked` says it did and the machine would not go further.
        Nothing remembers the travel it did not make.
        """
        for input_id in sorted(stopped):
            command = self.active.pop(input_id, None)
            if command is not None:
                command.status = 'blocked'

    def _runaway(self, reached, limit):
        named = ', '.join(identifier for identifier, _side, _bound in reached)
        return (
            f'{named} left a declared bound over this tick, and locating '
            f'the stop stopped no input that was moving -- after {limit} '
            f'event(s), one per input admitting travel. Every stop stops '
            f'at least one moving input, so this is a broken invariant of '
            f'the run rather than a coarse dt. The tick committed '
            f'nothing.')

    def _values(self, bank):
        """The bank, plus every INTERMEDIATE the program computes from
        it: a plain port or a derived coordinate a compiled edge
        determines, recomputed here rather than stored."""
        values = {self.keys[identifier]: value
                  for identifier, value in bank.items()}
        for edge in self.program.edges:
            if all(key in self.bank_keys for key in edge.gives):
                # Nothing this edge computes is an intermediate, so its
                # values were computed here and discarded. Skipping it is
                # behaviour-neutral and removes one graph evaluation per
                # law per tick -- and, with the refusal of a jumping law
                # that drives no owned coordinate, it means a jump graph
                # is never evaluated absolutely at all.
                continue
            for key, value in edge.values(values):
                if key not in self.bank_keys:
                    values[key] = value
        return values

    def _refuse(self, moved):
        """A tick that fails commits nothing, and every command that
        moved an input in it is retired reporting `refused` with the
        travel it had admitted before."""
        for command in moved:
            command.status = 'refused'
            self.active.pop(command.input, None)

    def _conflict(self, edge, predicted, received):
        coordinate = self.program.nodes[edge.slot_key].name
        binder = self.program.determiner.get(edge.slot_key)
        by = (f'{binder.description} (stated by {binder.stated_by})'
              if binder is not None else 'nothing in the program')
        return (
            f'{coordinate}: {edge.description}, stated by {edge.stated_by}, '
            f'predicts an increment of {predicted!r} over this tick, while '
            f'{by} gives it {received!r}. Two increments that disagree on '
            f'one coordinate are a conflict, and the framework does not '
            f'compare two values to decide which is right. The tick '
            f'committed nothing: the bank, the tick count and the tree '
            f'stand as they were, and the commands that moved an input in '
            f'it are retired as refused.')

    def _disagreement(self, edge, key, delta):
        coordinate = self.program.nodes[key].name
        return (
            f'{coordinate}: {edge.description}, stated by {edge.stated_by}, '
            f'gives it an increment of {delta!r} over this tick, while '
            f'another relation gives it {self.program.nodes[key].name} '
            f'a different one. Two increments that disagree on one '
            f'coordinate are a conflict; the tick committed nothing.')

    def _bounds(self):
        """Each declared bound as a NUMBER for this tick: evaluated once,
        at the tick's start, from the committed bank, so every segment of
        one tick is measured against the same number and the
        localization has a constant to solve against.

        A number bound costs nothing here; an expression bound costs one
        graph evaluation per tick. Its self-reference is well defined
        because the value it reads is committed and the value it bounds
        is not yet.
        """
        return [(identifier, self._bound(low, identifier),
                 self._bound(high, identifier), unit)
                for identifier, low, high, unit in self.spans]

    def _bound(self, bound, identifier):
        if bound is None or isinstance(bound, float):
            return bound
        return bound.evaluate({identifier: self.bank[identifier]})

    ##############################################
    # Snapshot, restore, reset

    def snapshot(self):
        return RunSnapshot(
            self.program.identity, self.dt, self.sim.tick,
            tuple(sorted(self.bank.items())),
            tuple(command.record() for command in self.active.values()))

    def restore(self, snapshot):
        if not isinstance(snapshot, RunSnapshot):
            raise TypeError(
                f'restore() takes a snapshot taken by sim.snapshot(), not '
                f'{snapshot!r}.')
        if snapshot.program != self.program.identity:
            raise ValueError(
                f'that snapshot was taken over the program '
                f'{snapshot.program}, and this simulation runs '
                f'{self.program.identity}. A snapshot restores into the '
                f'machine it was taken from: its coordinates, its inputs '
                f'and its relations are what its bank means.')
        if snapshot.dt != self.dt:
            raise ValueError(
                f'that snapshot was taken at dt={snapshot.dt} and this '
                f'simulation steps at dt={self.dt}. A command admits its '
                f'travel per tick, so a bank restored across two step '
                f'sizes would replay a different movement.')
        for command in self.active.values():
            command.status = 'cancelled'
        self.active = {}
        for record in snapshot.commands:
            (input_id, kind, native, native_rate, ticks, started,
             admitted, status) = record
            declaration = self.sim.drivers[input_id].declaration
            command = Command(
                input_id, kind, declaration, started, native=native,
                native_rate=native_rate, ticks=ticks,
                value=dict(snapshot.bank)[input_id] - admitted)
            command.admitted_native = admitted
            command.status = status
            self.active[input_id] = command
        self.bank = dict(snapshot.bank)
        self.sim.tick = snapshot.tick
        if self.ring is not None:
            self.ring.clear()
            self.crossing_ring.clear()
            self.stop_ring.clear()
        self.bind()

    def reset(self):
        self.restore(self.initial)


##############################################
# Construction helpers


def _driver_values(sim):
    return {identifier: state.value
            for identifier, state in sim.drivers.items()}


def _clamped(t):
    """A located fraction, held inside the stretch it was located on."""
    return 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)


def _record(crossings, found, first, last):
    """A segment's crossings, their fractions mapped back to the TICK.

    A segment's partition is in the fraction of the SEGMENT, and a
    `Crossing`'s `t` is documented as the fraction of the tick: without
    this the same crossing would be reported at a different fraction
    depending on whether a stop happened to cut the tick after it.
    """
    if crossings is None or not found:
        return
    width = last - first
    crossings.extend(replace(entry, t=first + entry.t * width)
                     for entry in found)


def _ring(record):
    """The bounded recording a running simulation keeps, or None.

    Unbounded recording is not offered under a running root: a run that
    never wraps would grow without limit, and a caller wanting more than
    the ring uses `every()`, which sees each tick as it happens.
    """
    if record is None:
        return None
    if isinstance(record, bool) or not isinstance(record, int) or record < 1:
        raise ValueError(
            f'record={record!r} is not a number of ticks to keep. Under a '
            f'running root recording is explicit and bounded: record=None '
            f'keeps nothing, and record=N keeps a ring of the most recent '
            f'N ticks.')
    return deque(maxlen=record)
