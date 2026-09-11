# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Values that flow between nodes, including the root's own time channel.

A driver's state is a number in the driver's own native unit -- a
stepper counts microsteps, a leadscrew turns degrees -- while the
geometry consuming it works in design units. A port is where that
conversion is declared once, next to the mechanism that owns it,
instead of being open-coded into every render() that reads the driver.

Two things are deliberately separate here. The DECLARATION is a class
attribute: stateless metadata (domain, unit, direction, scale) shared
by every instance of the node class, and readable off the class itself
so later tooling can enumerate a mechanism's connection points without
constructing it. The bound VALUE lives in a per-instance slot the
descriptor materializes on first access, so two instances of one node
class never share a value. The spike (ADR-056, spike/FINDINGS.md seam
2) conflated the two for drivers and had to reset() its way out; ports
do not repeat that.

Ports are kinematic in this version: a port carries an effort-like
value only. The bond-graph flow variable (torque, force) ADR-056
sketches is deliberately absent rather than half-present -- adding it
is a future spec change, and code written against a port that has no
flow slot cannot quietly come to depend on a wrong one.

The root's own time channel lives here too, as `Time`. `AssemblyNode.time`
is one entry of the driver snapshot with a symbolic fallback (ADR-008):
bound, it reports the bound number; unbound, solid2's `$t`, the
normalized 0..1 turn every document consumer plays. What that number
MEANS was the binder's choice -- a keyframe bound a fraction, a stepped
simulation bound seconds -- and nothing let the model settle it.

A root assembly settles it here::

    class WallClock(AssemblyNode):
        time = Time(loop=12 * 3600)

`loop` is the span of machine time, in seconds, that one turn of the
timeline covers. From then on `self.time` reads SECONDS on every path:
`$t * loop` when nothing is bound, so the published expressions carry
the conversion and `$t` stays the slider; the bound number under
`set_keyframe`, the testing decorators and `Sim`, all of which state
seconds. Every assembly below the root reads the root's time base.

The declaration is a data descriptor bound to the name `time` -- the
same shape `DriverDeclaration` has, and for the same reason: the
declaration is class metadata shared by every instance, the value
belongs to one node's snapshot, and `self.time` has to stay the single
read surface. It is not a driver: it is never enumerated into a
document's `drivers` table, has no default to bind, and is published as
`$t` already. `Time` reads as a port-kind thing for the same reason a
port does: a declaration descriptor with a per-instance value, which is
why it lives in this module rather than beside it.
"""

import math
from contextlib import contextmanager
from dataclasses import dataclass

from solid_node.node.phase import (current_enumeration, note_bound, note_read,
                                   note_unbound_read)


class BoundPort:
    """The per-instance value slot of one declared port.

    Holds no history: every simulate() rebinds it absolutely, exactly as
    an assembly's re-simulation expresses absolute kinematics. `value`
    is None until something binds it -- an unbound port is a wiring
    mistake to be seen, not a zero to be silently assumed. A read is
    reported to the lifecycle phase, so a render() that reads a port is
    known for the legacy render it is.
    """

    # The wiring that owns this slot, as (declaring class, child
    # attribute, keyword), or None. A wired coordinate has exactly one
    # binder: the wiring rebinds it at the end of every simulate() of
    # the parent that declared it, so a hand binding of the same slot
    # would be silently overwritten and is refused instead.
    wired_from = None

    # What bound the value this slot holds, for the current enumeration
    # of the tree: None for the author's own code, and otherwise
    # whatever the framework was binding as -- a wiring, a relation, a
    # derived coordinate. A coordinate has exactly one binder per
    # enumeration, and this is what a double binding is refused by.
    binder = None

    # The enumeration (solid_node.node.phase.Enumeration) whose bind
    # this value and binder belong to, or None before anything ever
    # bound this slot. See `clear_solved`.
    _enum_marker = None

    # The assembly whose OWN simulate phase most recently bound this
    # slot -- not necessarily the node the slot belongs to, which may be
    # a descendant several levels below whoever actually solved it -- or
    # None before anything bound it inside a phase. Set by
    # `phase.note_bound`; read by `couplings.ResolvedEnd.bound` to tell
    # a value still WAITING for that assembly's next attempt (this
    # enumeration) apart from one nothing due to run in this pass will
    # ever touch again.
    _bound_by = None

    def __init__(self, declaration, node):
        self.declaration = declaration
        self.node = node
        self._value = None

    @property
    def value(self):
        note_read('read port', self.declaration.name)
        if self._value is None:
            note_unbound_read(self)
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    @property
    def name(self):
        return self.declaration.name

    @property
    def domain(self):
        return self.declaration.domain

    @property
    def unit(self):
        return self.declaration.unit

    @property
    def out(self):
        return self.declaration.out

    @property
    def scale(self):
        return self.declaration.scale

    def __repr__(self):
        return (f'<{self.domain} port {self.name} of '
                f'{getattr(self.node, "name", self.node)}: {self.value}>')


class Coordinate:
    """What a port and a joint share as an END of a relation.

    `drives` is framework vocabulary and needs no import, so it lives on
    the declaration itself; the arithmetic is what builds a derived
    coordinate, `wrist + 2 * tool`. Both delegate to
    `solid_node.motion.couplings` through a local import: couplings
    imports THIS module (a relation relates two ports), so the edge only
    goes one way at module scope.
    """

    def drives(self, other, ratio=None, offset=None, law=None):
        from solid_node.motion.couplings import relate

        return relate(self, other, ratio, offset, law)

    def _ref(self):
        from solid_node.motion.couplings import coordinate_ref

        return coordinate_ref(self)

    def __add__(self, other):
        return self._ref() + other

    def __radd__(self, other):
        return self._ref() + other

    def __sub__(self, other):
        return self._ref() - other

    def __rsub__(self, other):
        return (-self._ref()) + other

    def __neg__(self):
        return -self._ref()

    def __mul__(self, other):
        return self._ref() * other

    def __rmul__(self, other):
        return self._ref() * other

    def __truediv__(self, other):
        return self._ref() / other

    def __float__(self):
        return float(self._ref())


class Port(Coordinate):
    """A port declaration, made as a class attribute on a node.

    A descriptor rather than an attribute created in __init__: the
    declaration must be readable off the CLASS (see declared_ports),
    and a node builds its children before calling super().__init__(),
    so there is no single point where instance ports could be created
    reliably. __get__ materializes the instance's slot lazily instead.
    """

    # Set by each subclass: what kind of quantity this port carries.
    domain = None

    # The class the declaration was made on, set by __set_name__. A
    # wiring error has to be able to say which class a coordinate
    # belongs to when it is not the one wiring it.
    owner = None

    def __init__(self, unit=None, out=False, scale=None):
        # `scale` is design units per native unit of whatever drives
        # this port -- millimetres per microstep, say. It belongs to
        # the SINK because the sink is what knows its own design units;
        # a source has no idea what it will be wired to.
        self.unit = unit
        self.out = out
        self.scale = scale
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name
        self.owner = owner

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        # Kept under one private key rather than as a public attribute:
        # _attr_name_for scans a node's __dict__ to derive child names
        # from the attributes holding them, and skips private keys.
        slots = instance.__dict__.setdefault('_port_values', {})
        slot = slots.get(self.name)
        if slot is None:
            slot = slots[self.name] = BoundPort(self, instance)
        return slot

    def __set__(self, instance, value):
        # Assignment binds, exactly as connect() does, scale applied:
        # `unit.crank = angle + phase` in a render() is the natural verb
        # for feeding a declared port. Defining __set__ also makes this a
        # DATA descriptor, so an assignment can never quietly replace the
        # declaration with a raw number that a later read trips over.
        bind(self.__get__(instance), value)

    def __repr__(self):
        return f'<{self.domain} port declaration {self.name}>'


_wiring_depth = 0

# What the framework is currently binding AS, or None when the binding
# is the author's own. Module state of exactly the same shape as
# `_wiring_depth` above, and for the same reason: `bind` is the one
# binding path, and what reaches it has to be able to say who it is
# without every caller threading an argument through.
_binder = None


@contextmanager
def binding_as(binder):
    """Inside this, every binding records `binder` as what bound it."""
    global _binder
    previous = _binder
    _binder = binder
    try:
        yield
    finally:
        _binder = previous


@contextmanager
def wiring_binding():
    """The wiring's own turn to bind: inside this, a wired coordinate
    accepts the binding it otherwise refuses.

    A wired coordinate has one binder, and it is the wiring. Everything
    else that reaches `bind` for such a slot -- an author's
    `self.wheel.turn = ...` in the parent that declared the wiring, a
    `connect()` into it -- is refused by name rather than silently
    overwritten at the end of the phase.
    """
    global _wiring_depth
    _wiring_depth += 1
    try:
        yield
    finally:
        _wiring_depth -= 1


def bind(sink, source):
    """Bind `sink`'s value from `source`, converting through the sink's
    declared scale. The one binding path: `connect()` and port
    assignment both come here.

    `source` is a bound port or a plain value; the value may be a
    symbolic animation expression, which flows through unresolved
    exactly as an operation value does. Binding belongs in simulate():
    done in render() it is reported to the phase like a read, because
    a once-only render() would bind once and never rebind.
    """
    note_read('bound port', sink.name)
    if sink.wired_from is not None and not _wiring_depth:
        parent, attribute, keyword = sink.wired_from
        raise ValueError(
            f"cannot bind '{keyword}' of {attribute}: {parent} declares "
            f"{attribute} = ...({keyword}=...), and that wiring binds it "
            f"at the end of every simulate() of {parent}. A wired "
            f"coordinate has one binder, so a binding here would be "
            f"overwritten; bind {parent}'s own coordinate instead, or "
            f"drop the wiring.")
    if isinstance(source, BoundPort):
        if source.value is None:
            # An unbound source is a wiring order mistake -- the
            # emitting node has not run yet -- and silently propagating
            # None would surface it much later, as a broken operation
            # value.
            raise ValueError(
                f'cannot connect {source.name} of '
                f'{getattr(source.node, "name", source.node)}: it has '
                'no value bound yet')
        value = source.value
    else:
        value = source
    if sink.scale is not None:
        value = value * sink.scale
    sink.value = value
    sink.binder = _binder
    # Which enumeration bound it, so a LATER assembly's `clear_solved`
    # -- reading its OWN stale record of having bound this same slot on
    # a PREVIOUS enumeration -- can tell that record apart from a FRESH
    # claim another assembly already made earlier in THIS one, and
    # leave that alone: two assemblies that alternate binding one
    # coordinate across runs (an ancestor's relation this run, this
    # node's own rest-default guard last run) must never have the
    # later one's belated clear erase the earlier one's fresh value.
    sink._enum_marker = current_enumeration()
    note_bound(sink)
    return sink


class RotationalPort(Port):
    """A port carrying an angle: a shaft, a crank, a stepper's count of
    microsteps around its own axis."""

    domain = 'rotational'


class TranslationalPort(Port):
    """A port carrying a position along an axis: a carriage, a piston,
    a lift."""

    domain = 'translational'


class SignalPort(Port):
    """A port carrying a dimensionless command value: an enable, a duty
    cycle, a setpoint -- something with no mechanical domain."""

    domain = 'signal'


def declared_ports(node_class):
    """Every port declared on `node_class`, by name.

    Reads the class dictionaries directly, so nothing is instantiated
    and no __get__ runs: a consumer can enumerate a mechanism's
    connection points from the class alone. Walked base-first so a
    subclass redeclaring an inherited port wins.

    A JOINT's coordinate is reported here too, under the joint's name,
    so every consumer of a node's connection points sees it without
    knowing what a joint is. The seam is the duck-typed `coordinate`
    attribute rather than an `isinstance` check on `Joint`, because
    `solid_node.motion.joints` imports THIS module -- a joint owns a
    port -- and importing it back would close the cycle. A registry
    would be state where none is needed; one attribute is the whole
    contract, and a project adding a joint kind of its own inherits it.
    A DERIVED COORDINATE -- a linear formula over other coordinates,
    declared in a class body -- is reported here for the same reason and
    through the same seam: it owns a port carrying the domain and unit
    its terms share.

    A joint owning SEVERAL coordinates -- a `Free` -- offers them as a
    `coordinates` mapping whose keys are the names they already carry,
    `<joint name>.<coordinate name>`, and every one of them is reported
    under that name. So an enumerated port name is NOT guaranteed to be
    a Python identifier: a consumer reaches a coordinate by the name
    reported here, never by `getattr` on the node.
    """
    ports = {}
    for klass in reversed(node_class.__mro__):
        for name, value in vars(klass).items():
            if isinstance(value, Port):
                ports[name] = value
                continue
            owned = getattr(value, 'coordinates', None)
            if (isinstance(owned, dict) and owned
                    and all(isinstance(port, Port)
                            for port in owned.values())):
                # A joint of any arity: the keys are already the full
                # names, so a joint owning one reports it under its own
                # name exactly as it always did.
                ports.update(owned)
            elif isinstance(getattr(value, 'coordinate', None), Port):
                ports[name] = value.coordinate
    return ports


def set_coordinate(node, name, value):
    """Bind the coordinate `name` of `node`, whatever kind of name it
    is: the one binding path a relation and a wiring take, and the one
    an author's own assignment takes.

    A name of one segment is an attribute of the node, and this is
    `setattr`. A name of several -- a coordinate of a joint owning
    several, `pose.roll` -- is NOT an attribute of the node, and
    `setattr(node, 'pose.roll', value)` would silently create an
    instance attribute and bind nothing; the head is read and the tail
    assigned on what it yields, so the joint's own view binds it and
    re-places the body.
    """
    head, _dot, tail = name.rpartition('.')
    setattr(getattr(node, head) if head else node, tail, value)


def get_coordinate(node, name):
    """The bound slot of the coordinate `name` of `node`, whatever kind
    of name it is: the reader that matches `set_coordinate`, and the
    pair that makes a name `declared_ports` reports a name the
    framework can read back as well as write.

    Mirrors `set_coordinate` segment for segment: a name of one part is
    an attribute of the node, and a name of several -- `pose.roll` -- is
    the head read and the tail taken off what it yields. What is
    returned is the SLOT -- the same `BoundPort` `node.pose.roll` itself
    yields, carrying the coordinate's domain, unit and scale -- not its
    value, so a slot nothing has bound reads back with `value is None`
    rather than being confused with a name that names no coordinate at
    all.

    A name the enumerator does not report is refused by name, naming
    the node, the name asked for and the names it does report, rather
    than answered with `None`: the membership test is against
    `declared_ports`, not against `getattr`, so a declared PARAMETER
    whose name resembles a coordinate's cannot answer for one.
    """
    reported = declared_ports(type(node))
    if name not in reported:
        names = ', '.join(sorted(reported)) or 'none'
        raise AttributeError(
            f"{type(node).__name__} has no coordinate '{name}'; "
            f"declared_ports reports: {names}.")
    head, _dot, tail = name.rpartition('.')
    return getattr(getattr(node, head) if head else node, tail)


@dataclass(frozen=True)
class Time:
    """A root assembly's time base: `time = Time(loop=<seconds>)`.

    Frozen on purpose, like a driver declaration: an attribute that
    could be assigned here would be state shared by every node of the
    class. Readable off the class (`Root.time.loop`) without
    constructing anything, so a producer can publish the loop the way
    it publishes the driver table.
    """

    loop: float

    def __post_init__(self):
        loop = self.loop
        if (isinstance(loop, bool) or not isinstance(loop, (int, float))
                or not math.isfinite(loop) or loop <= 0):
            raise ValueError(
                f'Time(loop=...) must be a positive finite number of '
                f'seconds, the span of machine time one turn of the '
                f'timeline covers; got {loop!r}')
        object.__setattr__(self, 'loop', float(loop))

    def __set_name__(self, owner, name):
        if name != 'time':
            raise TypeError(
                f"{owner.__name__}.{name}: a time base is declared as "
                f"'time', the property every simulate() reads; "
                f"'{name}' would leave nothing to tie it to. Write "
                f"time = Time(loop=...).")
        from solid_node.node.assembly import AssemblyNode
        if not issubclass(owner, AssemblyNode):
            raise TypeError(
                f'{owner.__name__} cannot declare a time base: only an '
                f'AssemblyNode animates, so only an AssemblyNode has a '
                f'time to declare the base of.')

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        from solid_node.node.assembly import read_time
        return read_time(instance)

    def __set__(self, instance, value):
        raise AttributeError(
            f'time of {type(instance).__name__} cannot be assigned: its '
            f'value belongs to the bound snapshot. Use '
            f'set_keyframe({value!r}) -- in seconds, under a declared '
            f'time base.')


def declared_time(cls):
    """The `Time` declaration of `cls`, or None when it declares none.

    Base-first through the MRO, stopping at the first `time` found: a
    subclass inherits its parent's declaration, and a class whose
    nearest `time` is the base property declares nothing. A class with
    no `time` at all -- not a node -- declares nothing either.
    """
    for klass in getattr(cls, '__mro__', ()):
        found = vars(klass).get('time')
        if found is None:
            continue
        return found if isinstance(found, Time) else None
    return None
