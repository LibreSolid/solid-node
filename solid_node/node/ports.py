# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Domain-typed connection points on nodes.

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
"""


class BoundPort:
    """The per-instance value slot of one declared port.

    Holds no history: every render rebinds it absolutely, exactly as an
    assembly re-render expresses absolute kinematics. `value` is None
    until something binds it -- an unbound port is a wiring mistake to
    be seen, not a zero to be silently assumed.
    """

    def __init__(self, declaration, node):
        self.declaration = declaration
        self.node = node
        self.value = None

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


class Port:
    """A port declaration, made as a class attribute on a node.

    A descriptor rather than an attribute created in __init__: the
    declaration must be readable off the CLASS (see declared_ports),
    and a node builds its children before calling super().__init__(),
    so there is no single point where instance ports could be created
    reliably. __get__ materializes the instance's slot lazily instead.
    """

    # Set by each subclass: what kind of quantity this port carries.
    domain = None

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


def bind(sink, source):
    """Bind `sink`'s value from `source`, converting through the sink's
    declared scale. The one binding path: `connect()` and port
    assignment both come here.

    `source` is a bound port or a plain value; the value may be a
    symbolic animation expression, which flows through unresolved
    exactly as an operation value does.
    """
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
    """
    ports = {}
    for klass in reversed(node_class.__mro__):
        for name, value in vars(klass).items():
            if isinstance(value, Port):
                ports[name] = value
    return ports
