# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Instance-qualified driver identity: the id, the token, the walk.

A driver name is declared class-locally, so it says nothing about WHICH
instance holds it. Everything that has to address a driver from outside
the node -- the serialized document, the simulation bank, an
instruction target, `set_state` -- is a flat namespace, and two
instances of one class collide there. The cure (ADR-056 stage 3a) is an
id derived from the node's position in the tree:

    <dotted path from the addressing root>.<class-local driver name>

`x_axis.motor`. A driver declared on the root itself keeps its bare
name. The id is COMPUTED, never stored: a render rebuilds the tree
every pass, so identity has to derive from tree position, and a
registry of assigned ids would be exactly the state ADR-056's one
guardrail forbids.

The path segments are the names `_link_child` derives from the
attribute the parent holds a child under -- the same names the
serialized document already publishes for nodes -- so the id in the
document and the key in a bank are the same string by construction.
That has one hard consequence: a name exists only AFTER its parent
linked the child. A pass that has not linked cannot qualify, and
falling back to the bare local name would silently give two instances
one id, which is the defect this module exists to remove. So it
raises instead.

Two things live here rather than in the simulation layer, for one
reason: `solid_node/node/` never imports `solid_node/simulation/`.

- `DriverDeclaration` is the marker the node layer recognizes, AND the
  descriptor that hands the bound value back. The node layer has to
  know that a class attribute IS a driver declaration -- to qualify it,
  to deliver a state entry to it, to tell an ambiguous bare name from
  an unambiguous one -- and delivering the entry and handing it back
  are the same responsibility over the same `_states` dict, so the
  read lives here rather than in `simulation/driver.py`. What a driver
  MEANS (native units, dtype rounding, ramps) stays in the simulation
  layer, which owns the `Driver` that subclasses this. `Port` next
  door is the same shape for the same reason.
- `DriverToken` is the symbolic read of one driver. It subclasses
  solid2's `OpenSCADConstant`, so ordinary project arithmetic and
  `solid_node.math`'s degree-trig symbolic mode produce a well-formed
  wire expression with no operator overloads and no expression tree to
  maintain (spike/expressions/FINDINGS.md, recommended representation).
"""

import re

from solid2.core.object_base import OpenSCADConstant

from .phase import note_read


class DriverIdError(ValueError):
    """A driver's qualified id cannot be computed, or would not be a
    legal identifier in the runtimes that evaluate it."""


class DriverDeclaration:
    """Marker base for a driver declaration, and the descriptor that
    reads one (see the module docstring).

    A driver is declared as a class attribute and read as an attribute
    of the instance -- `x = Driver(...)` is read `self.x` -- which is
    exactly how a `Port` is declared and read, and for the same
    reason: the declaration is class metadata shared by every
    instance, while the value belongs to one node's snapshot. It is
    the ONLY way to read a driver value; there is no mapping view of
    the snapshot to read it through instead.

    A DATA descriptor, deliberately. A `__get__`-only descriptor loses
    to an instance attribute of the same name, so `self.x = 5` would
    silently shadow the driver for every later read and surface as
    wrong geometry rather than as an error. Defining `__set__` makes
    the instance dict lose instead -- and keeps `_attr_name_for`,
    which derives child names by scanning a node's `__dict__`,
    seeing exactly what it saw before.
    """

    # Set by __set_name__; a default so an unbound declaration that
    # was never assigned to a class attribute still reports something.
    _name = None

    def __set_name__(self, owner, name):
        for klass in owner.__mro__[1:]:
            existing = vars(klass).get(name)
            if existing is None or isinstance(existing, DriverDeclaration):
                # Absent, or an inherited declaration this one
                # overrides -- base-first discovery lets a subclass
                # redeclare, and that stays legal.
                continue
            raise TypeError(
                f"driver '{name}' on {owner.__name__} would shadow "
                f"{klass.__name__}.{name}, which a driver read would then "
                f"hide for good. A driver is read as an attribute of its "
                f"node, so its name has to be free on that node: rename "
                f"the driver.")
        # object.__setattr__ because the simulation layer's Driver is a
        # frozen dataclass. A private non-field slot, not a `name`
        # field, so where a declaration is bound never enters the
        # generated __eq__/__hash__/__repr__.
        object.__setattr__(self, '_name', name)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        note_read('read driver', self._name)
        try:
            return instance._states[self._name]
        except (AttributeError, KeyError):
            # AttributeError: a node with no snapshot at all (a leaf).
            # KeyError: a snapshot that has no entry for this driver.
            # Both mean the same thing to the caller, and neither is a
            # value this layer may invent -- the declaration states a
            # default, and binding it is the loader's or the
            # simulation's job, never a silent fallback here.
            raise AttributeError(
                f"driver '{self._name}' of "
                f"{type(instance).__name__} is not bound; bind it with "
                f"set_state({self._name}=...)") from None

    def __set__(self, instance, value):
        raise AttributeError(
            f"driver '{self._name}' of {type(instance).__name__} cannot be "
            f"assigned: its value belongs to the bound snapshot. Use "
            f"set_state({self._name}={value!r}).")

    def drives(self, other, ratio=None, offset=None, law=None):
        """This driver drives `other`: a root driver reaches a joint at
        any depth without every class between them forwarding a port.

        A driver is a SOURCE only -- naming one as the DRIVEN end is
        refused where it is written, for the reason an assignment to one
        is refused: its value belongs to the bound snapshot.
        """
        from solid_node.motion.couplings import relate

        return relate(self, other, ratio, offset, law)


# A segment of a qualified id must be a name in every runtime that
# evaluates the expression it lands in -- jokenizer in the widget,
# OpenSCAD on the scad path. `_attr_name_for` derives `<attr>-<index>`
# for a list-held child, which is a perfectly good NODE name and parses
# as a subtraction here. v1 forbids it loudly; bijective sanitization is
# a recorded, compatible extension for when a project needs drivers on
# list-held children.
_LEGAL_SEGMENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')


def driver_id(path, name):
    """The qualified id of driver `name` on a node at `path`.

    `path` is the tuple of linked child names from the addressing root
    down to the declaring node, so a root-declared driver qualifies to
    its bare name.
    """
    for segment in path:
        if not _LEGAL_SEGMENT.fullmatch(segment):
            raise DriverIdError(
                f"cannot qualify driver '{name}' through node segment "
                f"'{segment}': a qualified driver id must be a legal "
                f"identifier in the runtimes that evaluate it, and "
                f"'{segment}' is not (a list-held child is named "
                f"<attribute>-<index>). Hold the node on its own "
                f"attribute, or move the driver off it.")
    return '.'.join(path + (name,))


def instance_path(node, root):
    """`node`'s path of linked names below `root`, `()` for the root.

    Walks `_parent` upwards, which is the link `_link_child` makes. A
    node that never reached `root` that way is not linked under it, and
    its name is therefore not derived -- so there is no id to compute
    and no bare-name fallback to fall back to.
    """
    parts = []
    current = node
    while current is not root:
        parent = getattr(current, '_parent', None)
        if parent is None:
            raise DriverIdError(
                f"cannot qualify {type(node).__name__} '{node.name}': it is "
                f"not linked under {type(root).__name__} '{root.name}', so "
                f"its instance path is not computable. Qualification only "
                f"happens in a pass that links parents to children before "
                f"recursing.")
        parts.append(current.name)
        current = parent
    return tuple(reversed(parts))


class DriverToken(OpenSCADConstant):
    """A symbolic read of one driver: a constant whose string IS its
    qualified id.

    Subclassing `OpenSCADConstant` is the whole trick. solid2's
    arithmetic is string-eager and flattens to the base class, which
    costs nothing here because the id is final at the moment the token
    is made; and `solid_node.math` dispatches on
    `isinstance(x, OpenSCADConstant)`, so degree trig wraps the id in
    OpenSCAD call strings exactly as it does for `$t`.
    """

    def __init__(self, qualified_id):
        self.driver_id = qualified_id
        super().__init__(qualified_id)


# Per-class cache of the declaration scan. Class attributes do not
# change at runtime, and a stepping loop asks this question for every
# node of the tree on every tick.
_declared_cache = {}


def declared_drivers_of(node_class):
    """Every driver declared on `node_class`, by class-local name.

    Reads the class dictionaries directly, so nothing is instantiated:
    the declaration is class metadata, exactly as `declared_ports` reads
    a mechanism's connection points. Walked base-first so a subclass
    redeclaring an inherited driver wins.
    """
    cached = _declared_cache.get(node_class)
    if cached is None:
        found = {}
        for klass in reversed(node_class.__mro__):
            for name, value in vars(klass).items():
                if isinstance(value, DriverDeclaration):
                    found[name] = value
        cached = _declared_cache[node_class] = found
    return cached


def drive_tree(root, resolve, visit=None):
    """Walk `root`'s tree in linked order, binding driver values, and
    return `{qualified_id: declaration}` for every driver found.

    This is the one mechanism every qualified pass shares: the
    simulation's enumeration, the document's symbolic serialization
    mode, and the loader's default binding all differ only in what
    `resolve(node, path, name, declaration)` returns.

    The ORDER is the load-bearing part, and mirrors
    `InternalNode.as_scad` and `core/serializer.serialize_node`: bind
    EVERY node's drivers over the tree, linking each child before
    recursing into it so a child's own read already knows its derived
    name and parent -- then render the tree, ONCE, which is where
    expressions are built and an unbound driver would fail loudly. That
    is what makes eager qualification correct rather than lucky, and
    (`whole-tree-fixpoint`) it is also what a NESTED driver needs: a
    render() now drives every descendant's simulate phase in one pass,
    so a node two levels down would otherwise have its phase run, and
    fail on its own still-unbound driver, before this walk ever
    reached it to bind one.

    Binding writes the node's snapshot directly rather than going
    through `set_state`. That is deliberate: `_validate_state` judges
    every value a plain number, and the symbolic mode's values are
    deliberately not numbers. The numeric door stays as strict as it
    was; this is a different door, and it never leaves holes -- it binds
    every declared driver of the tree or raises.

    `visit(node, path)`, when given, is called for every assembly in the
    walk after its drivers are bound and before anything in the tree
    renders, so a caller that also needs something else declared per
    node (instructions) pays for one walk rather than two.
    """
    # Deferred: `assembly` is `qualified`'s own caller (AssemblyNode's
    # module already imports THIS one, for `declared_drivers_of` and
    # `driver_id`), so the import has to wait until this function is
    # actually called, once both modules exist.
    from .assembly import _rest_children

    found = {}

    def deliver(node, path):
        states = getattr(node, '_states', None)
        if states is None:
            # A leaf holds no snapshot and no children of its own: the
            # same tolerance set_state has always had.
            return
        for name, declaration in declared_drivers_of(type(node)).items():
            identifier = driver_id(path, name)
            found[identifier] = declaration
            states[name] = resolve(node, path, name, declaration)
        if visit is not None:
            visit(node, path)
        # Rest-only: discovers structure and links exactly as a render()
        # would, without opening a phase or an enumeration, so every
        # node's OWN drivers are bound before ANY of them simulates.
        for child in _rest_children(node):
            deliver(child, path + (child.name,))

    deliver(root, ())
    if getattr(root, '_states', None) is not None:
        root.render()
    return found
