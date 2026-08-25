# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Driver declarations, the state a running simulation owns, and the
programs that advance it.

A driver is the only holder of simulation state: geometry stays a pure
function of the snapshot a tick produces (ADR-056's one guardrail).
That makes the split below the load-bearing decision of this module.
The DECLARATION is frozen class metadata -- default, range, unit, an
optional integer dtype, an optional scale in design units per native
unit -- readable off the class exactly as declared_ports reads a
mechanism's connection points, so a UI or a report can enumerate a
machine's inputs without constructing it. The STATE is built per
simulation, so two simulations over nodes of the same class cannot
observe each other and there is nothing to reset between runs. The
spike conflated the two and had to reset() its way out
(spike/FINDINGS.md seam 2); this does not repeat that.

Integer state is not a detail either. A stepper's position IS a whole
number of microsteps, and a ramp that distributes its delta by floor
division never lets a float into the trajectory -- which is what makes
"the same scenario twice" decidable by exact comparison rather than by
tolerance (the ADR-050 reasoning applied to simulation state).

This module deliberately imports nothing from solid_node.node: the
dependency runs one way only, so a node that declares no driver never
pulls the simulation layer in.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Driver:
    """A driver declaration, made as a class attribute on an assembly.

    Frozen on purpose: an attribute that could be assigned here would
    be state shared by every node of the class and every simulation
    over it. `scale` is design units per native unit -- millimetres per
    microstep, say -- and is what lets an instruction state a target in
    the units a maker thinks in while the state stays native.
    """

    default: object
    range: tuple = None
    unit: str = None
    dtype: type = None
    scale: float = None

    def __post_init__(self):
        if self.dtype not in (None, int, float):
            raise TypeError(
                f'driver dtype must be int, float or None, not {self.dtype!r}')
        if self.dtype is int and not isinstance(self.default, int):
            raise TypeError(
                f'an integer driver counts whole native units, so its '
                f'default must be an int, not {self.default!r}')

    def native(self, target):
        """`target`, expressed in design units, as native driver state.

        The rounding happens ONCE, here, at the moment a design-unit
        target becomes machine state -- never per tick, where repeated
        rounding would let the ramp drift off its landing.
        """
        value = target if self.scale is None else target / self.scale
        return round(value) if self.dtype is int else value


def declared_drivers(node_class):
    """Every driver declared on `node_class`, by name.

    Reads the class dictionaries directly, so nothing is instantiated:
    a consumer can enumerate a machine's inputs from the class alone.
    Walked base-first so a subclass redeclaring an inherited driver
    wins -- the same discovery declared_ports performs, deliberately,
    because the two declarations answer the same kind of question.
    """
    drivers = {}
    for klass in reversed(node_class.__mro__):
        for name, value in vars(klass).items():
            if isinstance(value, Driver):
                drivers[name] = value
    return drivers


class Program:
    """The contract a driver program answers.

    `value_at(k)` is a pure function of the tick number k counted from
    the program's start and of whatever start state the program
    captured: no accumulation, no dependence on how many times it has
    been asked. That purity is what lets a simulation be replayed, and
    what keeps two runs of one scenario exactly equal.

    `ticks` is how long it lasts; a state whose program has run that
    many ticks has arrived and drops it.
    """

    ticks = 0

    def value_at(self, k):
        raise NotImplementedError


class RampProgram(Program):
    """A linear ramp: `delta` distributed over `ticks` ticks.

    For an integer driver the distribution is `start + delta*k//n`, so
    every intermediate value is a whole native unit and k == n lands
    exactly on the target -- floor division cannot accumulate the error
    that repeated float addition would. A float driver gets the same
    shape without the integer guarantee, and lands exactly for the same
    reason: the endpoint is returned, not computed.
    """

    def __init__(self, start, target, ticks, dtype=None):
        self.start = start
        self.target = target
        self.ticks = ticks
        self.dtype = dtype
        self.delta = target - start

    def value_at(self, k):
        if k >= self.ticks:
            return self.target
        if self.dtype is int:
            return self.start + (self.delta * k) // self.ticks
        return self.start + self.delta * k / self.ticks

    def __repr__(self):
        return (f'<ramp {self.start} -> {self.target} '
                f'over {self.ticks} ticks>')


class DriverState:
    """The mutable half of one driver, owned by one simulation.

    Holds the current value and the program currently moving it, plus
    the tick that program started on -- the program itself stays pure,
    so the elapsed count has to live somewhere, and here it is per
    simulation like everything else that changes.
    """

    def __init__(self, name, declaration):
        self.name = name
        self.declaration = declaration
        self.value = declaration.default
        self.program = None
        self.started = 0

    def ramp_to(self, target, ticks, tick):
        """Start ramping to `target` (in NATIVE units) over `ticks`,
        from wherever this driver stands at `tick`."""
        self.program = RampProgram(self.value, target, ticks,
                                   self.declaration.dtype)
        self.started = tick

    def advance(self, tick):
        """This driver's value at `tick`, after its program has had its
        say. A driver with no program holds what it had."""
        if self.program is not None:
            elapsed = tick - self.started
            self.value = self.program.value_at(elapsed)
            if elapsed >= self.program.ticks:
                self.program = None
        return self.value

    def __repr__(self):
        return f'<driver {self.name}: {self.value}>'


def driver_states(node_class):
    """A fresh state bank for every driver `node_class` declares, each
    starting at its declared default. One simulation, one bank."""
    return {name: DriverState(name, declaration)
            for name, declaration in declared_drivers(node_class).items()}
