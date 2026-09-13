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
from dataclasses import dataclass, field

from solid_node.motion.joints import JointRangeError, declared_joints
from solid_node.motion.ports import RunBinder, get_coordinate

from .driver import RampProgram
from .program import (compile_program, qualified_coordinates,
                      TooManyCrossings, UnsupportedLaw)


# Two increments agree when they are within this of each other,
# relatively: the tick's arithmetic is a difference of two evaluations,
# so two routes to one coordinate differ in the last bits rather than
# not at all.
_TOLERANCE = 1e-9


class RunConflict(ValueError):
    """Two increments disagreed on one coordinate over one tick. The
    tick committed nothing."""


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
    `refused` and `cancelled`; `blocked` cannot occur in this cycle,
    where a range fails the tick rather than stopping the group, and the
    vocabulary is fixed now so cycle 3 adds no word to it.
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
        return math.floor(travelled) if self.declaration.dtype is int \
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
        # inside a tick. `record=None` builds neither, so a run that
        # records nothing pays nothing for the record.
        self.crossing_ring = _ring(record)
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
        self.spans = _declared_spans(coordinates)

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
        if native < 0:
            raise ValueError(
                f"move('{input_id}', ...) would travel backwards "
                f'({_design(declaration, native)} in design units). A '
                f'reverse move is refused in this cycle: reverse travel '
                f'meets no stop until a joint range becomes a physical '
                f'stop.')
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
        if rate < 0:
            raise ValueError(
                f"rate('{input_id}', {rate!r}) would run backwards. A "
                f'reverse rate is refused in this cycle: reverse travel '
                f'meets no stop until a joint range becomes a physical '
                f'stop.')
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
        """Design.md section 7, over increments only: nothing is bound
        until the commit, so a refused tick touches no slot."""
        program = self.program
        deltas = {key: 0.0 for key in program.nodes}
        admissions = {}
        for input_id, command in self.active.items():
            if only is not None and command is not only:
                admissions[input_id] = 0
                continue
            admissions[input_id] = command.admits(tick, self.dt)
        moved = [self.active[input_id] for input_id, delta
                 in admissions.items() if delta]
        for input_id, delta in admissions.items():
            if delta:
                deltas[self.keys[input_id]] = delta

        values = self._values()
        determined = set()
        # A fresh list per tick, appended to the ring only on COMMIT, so
        # a refused tick records no crossing.
        found = None if self.crossing_ring is None else []
        for edge in program.edges:
            if edge.kind == 'check':
                predicted = edge.predicts(deltas, constant=0.0)
                received = deltas[edge.slot_key]
                if not _agree(predicted, received):
                    self._refuse(moved)
                    raise RunConflict(self._conflict(
                        edge, predicted, received))
                continue
            try:
                increments = edge.increments(values, deltas, found, tick)
            except (TooManyCrossings, UnsupportedLaw):
                # A tick a law cannot be integrated over commits
                # nothing, exactly as a conflict does.
                self._refuse(moved)
                raise
            for key, delta in increments:
                if key in determined and not _agree(deltas[key], delta):
                    self._refuse(moved)
                    raise RunConflict(self._disagreement(edge, key, delta))
                deltas[key] = delta
                determined.add(key)

        committed = {identifier: value + deltas.get(self.keys[identifier], 0.0)
                     for identifier, value in self.bank.items()}
        self._check_spans(committed, moved)

        # Nothing above bound anything. From here the tick is taken.
        self.bank = committed
        if advance:
            self.sim.tick = tick
        for input_id, delta in admissions.items():
            self.active[input_id].admitted_native += delta
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
            self.crossing_ring.extend(found)

    def _values(self):
        """The bank, plus every INTERMEDIATE the program computes from
        it: a plain port or a derived coordinate a compiled edge
        determines, recomputed here rather than stored."""
        values = {self.keys[identifier]: value
                  for identifier, value in self.bank.items()}
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

    def _check_spans(self, committed, moved):
        for identifier, low, high, unit in self.spans:
            value = committed[identifier]
            if low <= value <= high:
                continue
            self._refuse(moved)
            raise JointRangeError(
                f'{identifier} would reach {value!r} over this tick, '
                f'outside the range {low} to {high} {unit or "units"} its '
                f'joint declares. The tick committed nothing and the bank '
                f'stands at the last admitted tick: in this cycle a range '
                f'fails the tick rather than stopping the group it is '
                f'connected to.')

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
        self.bind()

    def reset(self):
        self.restore(self.initial)


##############################################
# Construction helpers


def _driver_values(sim):
    return {identifier: state.value
            for identifier, state in sim.drivers.items()}


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


def _declared_spans(coordinates):
    """`(qualified id, low, high, unit)` for every banked coordinate
    whose joint declares a range, resolved once."""
    found = []
    for identifier, (node, name) in sorted(coordinates.items()):
        for joint in declared_joints(type(node)).values():
            if name not in joint.coordinates:
                continue
            span = joint.arguments(node)[2]
            if span is not None:
                found.append((identifier, span[0], span[1], joint.unit))
            break
    return found
