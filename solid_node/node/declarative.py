# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The structure a class body declares: children, and how a body is
recognized as one.

A node class body declares three things -- tree structure, parameter
propagation and ports -- and the framework derives everything else. This
module holds the first. `solid_node.parameters` holds the second, and
`ports` next door the third; `DriverDeclaration` in `qualified.py` is the
precedent all of them follow: a declaration is class metadata shared by
every instance, read off the instance as a plain value, enumerable off the
class without constructing anything.

A node constructed inside a node class body is a DECLARATION of a child,
never an instance: an instance would be one object mutated by every
parent, which is the empirical fact that forces this whole model.
`AbstractBaseNode.__new__` asks `in_class_body()` and returns a
`ChildDeclaration` instead; each parent instance realizes its own child at
construction, top-down, with the tokens it was handed resolved against its
own values. Resolving them is the one service this module takes from the
parameter layer, through `evaluate`.

`NodeMeta` is what makes the class-body question answerable. Its
`__prepare__` hands the class statement a namespace of a private type,
and a node constructor recognizes an executing body by finding that
namespace as the locals of a frame on its stack. The namespace's own
identity is the signal rather than a counter kept in step by `__new__`,
because a body that raises -- a dimension error, on purpose -- never
reaches the metaclass `__new__`, and a counter would stay stuck. The
same namespace names each declaration the moment it is assigned, which
is what lets a dimension error in the next line of the body say `bore`
and `pressure_angle` instead of two anonymous tokens. It names a
parameter and a child alike, which is why it knows the parameter layer's
`Declaration` type.
"""

import sys

from solid_node.parameters import (Declaration, ParameterError,
                                   declared_parameters, evaluate)


class StructureError(RuntimeError):
    """A render changed which declared children are present."""


class SidewaysReadError(AttributeError):
    """A class body read a parameter off a sibling's declaration."""


##############################################
# Coordinates, recognized without importing them

# `solid_node.motion.ports` imports `solid_node.node.phase`, and
# `solid_node.motion.joints` imports ports, so this module -- which the
# node package imports while it is still initializing -- cannot import
# either at module scope in every import order. It does not need to:
# what makes a value a coordinate is that it IS a port declaration
# (a domain, a direction marker and a scale) or that it OWNS one as its
# `coordinate`. That is the same duck-typed seam `declared_ports` uses
# to report a joint's coordinate, stated once more here rather than
# turned into an import cycle or a registry.

def _is_port_declaration(value):
    return (getattr(value, 'domain', None) is not None
            and hasattr(value, 'scale') and hasattr(value, 'out'))


def _coordinate_of(value):
    """The port `value` offers as a coordinate: itself when it is a
    port declaration, its `coordinate` when it is a joint owning one,
    else None."""
    if _is_port_declaration(value):
        return value
    owned = getattr(value, 'coordinate', None)
    if _is_port_declaration(owned):
        return owned
    return None


def _coordinates_of(value):
    """The coordinates `value` owns when it owns SEVERAL -- a `Free`'s
    six, by the dotted names they carry -- and None otherwise.

    Without it a joint owning several is not recognised as a coordinate
    at all: passed to a child as a keyword it would be taken for a
    PARAMETER and reach the child's constructor, and a name declared as
    both such a joint and a port would keep whichever came last with no
    sign of the other. Both are refused by name instead.
    """
    owned = getattr(value, 'coordinates', None)
    if (isinstance(owned, dict) and len(owned) > 1
            and all(_is_port_declaration(port) for port in owned.values())):
        return owned
    return None


def _is_coordinate(value):
    """A port, a derived coordinate, or a joint of any arity."""
    return (_coordinate_of(value) is not None
            or _coordinates_of(value) is not None)


def _is_joint(value):
    return not _is_port_declaration(value) and _is_coordinate(value)


def _refuse_wiring_several(owner, attribute, keyword, joint, role):
    """A joint owning several coordinates named in a wiring, in either
    role.

    A wiring keyword is a name a class body can write as a keyword
    argument, which is what a port, a derived coordinate and a joint
    owning ONE coordinate are named. A coordinate of a joint owning
    several is named `<joint>.<coordinate>`, which is not one; the
    dotted keyword does reach here intact, and this version
    deliberately does not offer it. Such a coordinate is bound by
    assignment on the instance, or by a relation.
    """
    owned = ', '.join(joint.coordinates)
    first = next(iter(joint.coordinates))
    return (
        f"{owner.__name__}.{attribute}: '{keyword}' names the joint "
        f"'{joint.name}' {role}, and that joint owns "
        f"{len(joint.coordinates)} coordinates: {owned}. None of them is a "
        f"wiring keyword -- a coordinate of such a joint is bound by "
        f"assignment on the instance ({first} = ...) or by a relation "
        f"({first} at either end of drives) -- so there is nothing to wire "
        f"here.")


##############################################
# Site-declared joints

def _in_current_body(value):
    """Whether `value` is already bound to a name in the class body
    that is CURRENTLY EXECUTING -- the shape of a WIRING that names a
    sibling declared earlier in the same body (`turn = Revolute(...)`,
    then `wheel = Wheel(turn=turn)`), as opposed to a fresh `Joint(...)`
    built inline in the argument list, which was never assigned to any
    name at all. See `ChildDeclaration.__init__` for why `.owner is
    None` cannot tell the two apart on its own.
    """
    namespace = executing_body()
    if namespace is None:
        return False
    return any(held is value for held in namespace.values())


def _specialize(node_class, site_joints):
    """A subclass of `node_class` carrying `site_joints` as ordinary
    class attributes -- one specialization per declaration site, built
    once, in `ChildDeclaration.__init__`, and shared by every child the
    site realizes (design decision 6, "The declaration SPECIALIZES the
    child's class").

    Its `__qualname__`, `__name__`, `__module__` and `__doc__` are
    copied from `node_class` VERBATIM, and deliberately: a joint is not
    identity -- it says where a body may move, not what geometry is
    built -- so two children of one class differing only in the joints
    their sites passed must key one artifact
    (`base._build_uniq_id`/`_canonical_serialization` read the CLASS's
    `__qualname__` and the constructor arguments, and the joint keyword
    never reaches the constructor at all). `source_scope` scopes a
    digest by `klass.__name__` and `get_source_file` reads
    `inspect.getfile(self.__class__)`; both follow the copy to the
    written class's own file.

    Built through `type(node_class)` rather than through `NodeMeta`
    directly, so a project's own metaclass (the `NodeMeta` subclass
    docstring's own example) is preserved. Never bound to any module
    namespace: `node_classes_in`/`_defined_classes` scan a MODULE's
    `__dict__`, so a specialization nothing ever assigns to a module
    attribute is invisible to model discovery by construction, not by a
    second check.

    Every joint's own `__set_name__` fires exactly as it would for an
    ordinary class body -- `Joint._refuse_shadowing` runs against
    `node_class`'s own MRO (`type(...).__mro__[1:]` starts there), which
    is decision 10's refusal against a port, a parameter, a child
    declaration, a method or a property the child already answers to,
    and a site joint of a name `node_class` already declares REPLACES
    it and keeps its slot, because `declared_joints`'s base-first walk
    already reads a redeclaration that way (ADR-093).
    """
    namespace = dict(site_joints)
    namespace['__qualname__'] = node_class.__qualname__
    namespace['__module__'] = node_class.__module__
    namespace['__doc__'] = node_class.__doc__
    return type(node_class)(node_class.__name__, (node_class,), namespace)


def _refuse_constructor_shadowing(node_class, site_joints):
    """Design decision 10's row `Joint._refuse_shadowing` cannot see: a
    keyword naming a parameter of a NON-DECLARATIVE child's own
    `__init__`.

    Such a parameter is not a class attribute at all -- there is
    nothing for `_refuse_shadowing`'s scan of `vars(klass)` to find --
    and the keyword is stripped before construction like every site
    joint, so left unchecked the child would be built with no value for
    it at all: different geometry, silently. `VisualPack(filename=...)`
    and `Link(dir=...)` are why this reads the constructor's own
    signature and not only the class's attributes.
    """
    import inspect

    try:
        parameters = inspect.signature(node_class.__init__).parameters
    except (TypeError, ValueError):
        return
    for keyword in site_joints:
        if keyword in parameters:
            raise TypeError(
                f"{node_class.__name__}.__init__ takes a parameter "
                f"'{keyword}'. A site-declared joint of that name would "
                f"be stripped before construction -- a site joint is not "
                f"a parameter -- so {node_class.__name__} would be built "
                f"with no '{keyword}' at all: different geometry, "
                f"silently. Rename the joint, or declare it under a name "
                f"{node_class.__name__}'s constructor does not take.")


def _refuse_coordinate_name_collisions(node_class, site_joints, wiring):
    """Design decision 10's last two rows: two things naming the same
    COORDINATE, reachable only through `**{...}` expansion since one
    Python keyword cannot hold two values -- a `Free`'s own dotted
    sub-coordinate name (`pose.roll`) written again as a second, literal
    keyword; or a site joint and a wiring landing on the same name.

    Run once every site joint's own `__set_name__` has fired (inside
    `_specialize`), so a `Free`'s `coordinates` already carry their
    dotted names.
    """
    occupied = {}
    for keyword, joint in site_joints.items():
        for coordinate_name in joint.coordinates:
            occupied.setdefault(coordinate_name, set()).add(keyword)
    for keyword in wiring:
        occupied.setdefault(keyword, set()).add(keyword)
    for coordinate_name, keywords in occupied.items():
        if len(keywords) > 1:
            raise TypeError(
                f"{node_class.__name__} would receive the coordinate "
                f"'{coordinate_name}' more than once, from "
                f"{', '.join(sorted(keywords))}. One coordinate, one "
                f"declaration.")


##############################################
# Child declarations

class ChildDeclaration:
    """A node constructed in a class body: the class and the arguments,
    realized per parent instance.

    Not a data descriptor: after realization the parent's instance dict
    holds the real node under the same attribute, and that wins, so
    `_link_child`/`_attr_name_for` see exactly the tree they see today.
    Reading the attribute on the CLASS hands back the declaration, which
    is what `declared_children` and any later tooling want.
    """

    _name = None

    def __init__(self, node_class, args, kwargs):
        self.args = tuple(args)
        # A keyword whose VALUE is a coordinate is told apart from a
        # WIRING by the value, not the keyword (design decision 1): a
        # coordinate the DECLARING class already owns is a wiring, as
        # today; a fresh `Joint(...)` built right here in the keyword
        # list -- one that has never been assigned to any class body --
        # is a SITE declaration, a freedom the site is giving this
        # child rather than a value the site is handing it. A joint
        # already owned by some THIRD class falls through to `wiring`
        # and is refused there, where the declaring class is known and
        # the message can say so.
        #
        # `owner is None` alone cannot tell the two apart: `Joint`
        # deliberately does not carry `_names_in_body` (unlike a
        # `Declaration` or a `DerivedCoordinate`), so `turn =
        # Revolute(...)` followed two lines later by `wheel =
        # Wheel(turn=turn)`, in the SAME still-executing class body,
        # reads `turn.owner` as None too -- `__set_name__` fires for
        # every attribute in one batch, only once the class exists.
        # `_in_current_body` closes that gap: a joint already bound to
        # a name in the EXECUTING body's own namespace is a same-body
        # wiring reference, whatever `.owner` reads right now; a joint
        # bound to no name anywhere is a fresh site declaration.
        self.site_joints = {}
        for key, value in kwargs.items():
            if (_is_joint(value) and value.owner is None
                    and not _in_current_body(value)):
                # Marked the moment it is claimed: `Joint.place` reads
                # this to decide whether its arguments need carrying,
                # and nothing else ever sets it.
                value._declared_at_site = True
                self.site_joints[key] = value
        # A keyword whose VALUE is a coordinate -- a port or a joint
        # declared on the class whose body this is -- is a WIRING, not a
        # parameter: it says which value reaches the child at each
        # instant, not what geometry is built. Deciding on the value
        # rather than on the name is what keeps the parameter path
        # untouched: wirings never reach resolve_parameters, so they
        # never enter the child's construction or its identity, and
        # every other keyword keeps the meaning it has today.
        self.wiring = {key: value for key, value in kwargs.items()
                       if key not in self.site_joints and _is_coordinate(value)}
        self.kwargs = {key: value for key, value in kwargs.items()
                       if key not in self.site_joints
                       and key not in self.wiring}
        if self.site_joints:
            # Built HERE, not in __set_name__: a declaration held in a
            # literal list never receives __set_name__ (the same reason
            # a wiring in a list-held declaration goes unvalidated
            # today), and the specialization has to exist before any
            # class body reads a path through this declaration -- which
            # can happen on the very next line of the SAME body.
            _refuse_constructor_shadowing(node_class, self.site_joints)
            node_class = _specialize(node_class, self.site_joints)
            _refuse_coordinate_name_collisions(
                node_class, self.site_joints, self.wiring)
        self.node_class = node_class

    def __set_name__(self, owner, name):
        self._name = name
        if self.wiring:
            self._check_wiring(owner)

    def _check_wiring(self, owner):
        """Refuse a wiring at CLASS DEFINITION, where both ends are
        known: the value has to be a coordinate this class declares, and
        the keyword has to name a port or a joint the child declares.

        The same moment the sideways-read error fires, so a wiring
        mistake reads like the other class-body mistakes rather than
        surfacing as an unbound value somewhere down a render.
        """
        from solid_node.motion.joints import declared_joints
        from solid_node.motion.ports import declared_ports

        ours = {id(port) for port in declared_ports(owner).values()}
        ours.update(id(joint) for joint in declared_joints(owner).values())
        theirs = declared_ports(self.node_class)
        theirs_joints = declared_joints(self.node_class)
        for keyword, source in self.wiring.items():
            several = _coordinates_of(source)
            if several is not None:
                raise TypeError(_refuse_wiring_several(
                    owner, self._name, keyword, source,
                    'as a wiring source, passed whole to '
                    f'{self.node_class.__name__}'))
            named = keyword.partition('.')[0]
            owned = _coordinates_of(theirs_joints.get(named))
            if owned is not None:
                raise TypeError(_refuse_wiring_several(
                    owner, self._name, keyword, theirs_joints[named],
                    f'as a wiring target on {self.node_class.__name__}'))
            if id(source) not in ours:
                elsewhere = getattr(source, 'owner', None)
                if _is_joint(source) and elsewhere is not None:
                    # Design decision 10: a joint declared on a THIRD
                    # class, neither the declaring class nor the child
                    # -- refused by its own message, naming what the
                    # child itself declares, because a declaration
                    # object belongs to one class.
                    declares = ', '.join(sorted(theirs_joints)) or 'none'
                    raise TypeError(
                        f"{owner.__name__}.{self._name}: '{keyword}' names "
                        f"the joint {elsewhere.__name__}.{source.name}, "
                        f"declared on {elsewhere.__name__} -- a THIRD "
                        f"class, neither {owner.__name__} nor "
                        f"{self.node_class.__name__}. A joint declaration "
                        f"belongs to one class; {self.node_class.__name__} "
                        f"declares: {declares}. Either declare '{keyword}' "
                        f"on {owner.__name__} and wire it, or write a "
                        f"fresh joint at this site.")
                belongs = (f'{elsewhere.__name__} declares it'
                           if elsewhere is not None
                           else 'it is declared on no class here')
                raise TypeError(
                    f"{owner.__name__}.{self._name}: the coordinate wired "
                    f"as '{keyword}' is not declared on "
                    f"{owner.__name__} -- {belongs}. A wiring hands a "
                    f"parent's OWN coordinate to a child; declare it on "
                    f"{owner.__name__} and wire that.")
            if keyword not in theirs:
                declared = ', '.join(sorted(theirs)) or 'none'
                raise TypeError(
                    f"{owner.__name__}.{self._name}: "
                    f"{self.node_class.__name__} cannot receive a "
                    f"coordinate as '{keyword}', because it declares no "
                    f"port or joint of that name; it declares: "
                    f"{declared}.")

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        raise AttributeError(
            f"child '{self._name}' of {type(instance).__name__} is not "
            f"realized on this instance")

    def __getattr__(self, attribute):
        """What reading an attribute off a declaration means.

        A PORT, a JOINT, a derived coordinate or another CHILD
        DECLARATION yields a path reference: a place in the tree, which
        a class body may name, resolved per parent instance at
        realization. Everything else -- a declared parameter above all
        -- keeps the `SidewaysReadError` it has always raised, with the
        same advice. ADR-061's rule is extended, not reversed: a class
        body still may not read a sibling's VALUE.
        """
        if attribute.startswith('_'):
            raise AttributeError(attribute)
        from solid_node.motion.couplings import (BroadcastRef, PathRef,
                                                  read_through)

        held = f'{self._name}.{attribute}' if self._name else attribute
        found = read_through(self.node_class, attribute, held)
        if isinstance(found, RepeatDeclaration):
            # The first (and, so far, only) repeated segment this path
            # steps onto: a BROADCAST from here on, not a value -- the
            # couplings capability's own reading of a repeated child.
            return BroadcastRef(self, (attribute,), found, found)
        return PathRef(self, (attribute,), found)

    def drives(self, other, ratio=None, offset=None, law=None):
        """This child's ONE joint drives `other`: an arbor is one body
        turning at one bearing, and a class that is not is refused."""
        from solid_node.motion.couplings import relate

        return relate(self, other, ratio, offset, law)

    def __and__(self, other):
        from solid_node.motion.couplings import group_with

        return group_with(self, other)

    def repeat(self, count):
        """Count-many identical instances of this declaration."""
        return RepeatDeclaration(self, count)

    def realize(self, values, owner):
        """Construct this declaration's child against `values`, `owner`
        being the realized PARENT node itself (not its name): the frame
        a site-declared joint's arguments resolve against, and the
        object a site's callable is handed (design decision 5).

        `owner`'s own declared parameters are already resolved, its
        `check()` has already run, and every child it declared BEFORE
        this one has already been realized into its instance dict
        (`realize_children`'s loop sets each as it goes) -- exactly what
        a site's callable may read. `owner` has NOT rendered, so no
        placement exists yet, including this child's own; the CARRY
        that needs one happens later, at binding.
        """
        args = [evaluate(arg, values) for arg in self.args]
        kwargs = {key: evaluate(arg, values)
                  for key, arg in self.kwargs.items()}
        child = self.node_class(*args, **kwargs)
        if self.wiring:
            self._record_wiring(child, owner)
        if self.site_joints:
            self._resolve_site_joints(child, owner)
        return child

    def _resolve_site_joints(self, child, parent):
        """Resolve every site-declared joint's arguments against the
        DECLARING PARENT, eagerly, right here at the child's
        realization -- the reason `resolve_declared_joints` (already run
        inside the child's own constructor, above) skips a site joint
        entirely: the parent did not exist yet in there. Cached under
        the SAME `_joint_arguments` slot a class joint's own eager
        resolution uses, so `Joint.arguments`/`Joint.place` read either
        kind exactly alike from here on."""
        parent_values = parent.__dict__.get('_parameters', {})
        resolved = child.__dict__.setdefault('_joint_arguments', {})
        for name, joint in self.site_joints.items():
            resolved[name] = joint.resolve(parent, parent_values)

    def _record_wiring(self, child, owner):
        """Record on the realized child which of its coordinates a
        wiring feeds, so the parent binds them on every simulate()
        without re-deriving the mapping, and so a hand binding of a
        wired coordinate is refused where it happens."""
        from solid_node.motion.ports import declared_ports

        ports = declared_ports(type(child))
        recorded = child.__dict__.setdefault('_wired_from', {})
        for keyword, source in self.wiring.items():
            recorded[keyword] = source
            slot = ports[keyword].__get__(child)
            # `owner` is the realized PARENT node now, not its class
            # name -- read the name back out, so this message keeps
            # reading exactly as it always has.
            slot.wired_from = (type(owner).__name__, self._name, keyword)

    def __repr__(self):
        return f'<declared {self.node_class.__name__} {self._name or ""}>'


class RepeatDeclaration:
    """`declaration.repeat(count)`: count-many identical children, one
    geometry with count placements."""

    _name = None

    def __init__(self, declaration, count):
        self.declaration = declaration
        self.count = count

    def __set_name__(self, owner, name):
        self._name = name
        self._adopt(owner, name)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        raise AttributeError(
            f"children '{self._name}' of {type(instance).__name__} are not "
            f"realized on this instance")

    def __getattr__(self, attribute):
        """A repeated declaration names a PLACE too, exactly as a plain
        child declaration does: the coordinate it reaches is the same
        one of every realized copy, which is what makes it a BROADCAST
        (`solid_node.motion.couplings.BroadcastRef`) rather than an
        ordinary path -- usable as the DRIVEN end of a relation and
        refused as its source."""
        if attribute.startswith('_'):
            raise AttributeError(attribute)
        from solid_node.motion.couplings import BroadcastRef, read_through

        held = f'{self._name}.{attribute}' if self._name else attribute
        found = read_through(self.node_class, attribute, held)
        if isinstance(found, RepeatDeclaration):
            _refuse_two_repeats(held, self, found)
        return BroadcastRef(self, (attribute,), found, self)

    def drives(self, other, ratio=None, offset=None, law=None):
        """The repeat's own one joint, named as an end: reached here,
        rather than through `__getattr__`, so `beads.drives(x)` reaches
        the SOURCE refusal instead of a nonsense path error (`drives`
        is not an attribute `read_through` would find on the repeated
        class)."""
        from solid_node.motion.couplings import relate

        return relate(self, other, ratio, offset, law)

    def __and__(self, other):
        from solid_node.motion.couplings import group_with

        return group_with(self, other)

    def _adopt(self, owner, name):
        # The held declaration never reached the class namespace under
        # its own name, so it is named and validated through this one.
        self.declaration._name = name
        self.declaration.__set_name__(owner, name)
        self._check_index(owner, name)

    def _check_index(self, owner, name):
        """A repeated class that already answers to `index` is refused
        HERE, where the repeat is written: a copy's own position is
        stamped as a plain instance attribute, which a declaration of
        the same name -- a parameter, a port, a joint, a child, a
        property or a method -- wins over silently
        (evidence/probe_shadow.py). Checked on the REPEATED class only:
        a PARENT that happens to declare its own `index` (InMoov's
        `Hand`) is untouched."""
        node_class = self.declaration.node_class
        found = getattr(node_class, 'index', None)
        if found is None:
            return
        raise TypeError(
            f"{owner.__name__}.{name}: cannot repeat {node_class.__name__}, "
            f"which already declares 'index' ({found!r}). Each copy a "
            f"repeat realizes carries its own 0-based position as the "
            f"plain instance attribute 'index', and a declaration of that "
            f"name on {node_class.__name__} would win over it silently -- "
            f"the framework's value would sit in the instance dict, unread. "
            f"Rename {node_class.__name__}'s 'index', or declare the "
            f"children individually or in a list instead of repeating "
            f"them.")

    @property
    def node_class(self):
        return self.declaration.node_class

    def realize(self, values, owner):
        """`owner` is the realized PARENT node (see
        `ChildDeclaration.realize`); every copy realizes against the
        SAME parent and the SAME `values`, so a site-declared joint's
        arguments resolve to the same numbers for each -- what differs
        per copy is the CARRY, through that copy's own rest placement
        (design decision 8)."""
        count = evaluate(self.count, values)
        if isinstance(count, float) and count.is_integer():
            count = int(count)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ParameterError(
                f"{type(owner).__name__}: repeat count for '{self._name}' "
                f"must be a non-negative integer, got {count!r}")
        copies = []
        for index in range(count):
            child = self.declaration.realize(values, owner)
            # AFTER construction: a legacy (non-declarative) child calls
            # super().__init__() LAST, after building its own children,
            # so a slot consumed during __init__ would land on the wrong
            # node. No sighting needs `index` during construction (every
            # broadcast law is declared on the PARENT and read at the
            # end of ITS OWN construction, well after this); see
            # design.md decision 3.
            child.__dict__['index'] = index
            copies.append(child)
        return copies

    def __repr__(self):
        return (f'<declared {self.node_class.__name__} {self._name or ""} '
                f'x {self.count!r}>')


def _refuse_two_repeats(written, first, second):
    """A path passing through two repeated declarations: `legs.joints`
    where both `legs` and `joints` are `.repeat()`s. A broadcast fans
    out over exactly one repeat, because n x m relations from one
    sentence is not a thing a reader can count."""
    raise TypeError(
        f"'{written}' passes through two repeated declarations -- "
        f"'{first._name}' of {first.node_class.__name__} and "
        f"'{second._name}' of {second.node_class.__name__} -- and a "
        f"broadcast fans out over ONE repeat. State the relation inside "
        f"the more deeply repeated class instead.")


def _is_child_list(value):
    return (isinstance(value, list) and value
            and all(isinstance(item, ChildDeclaration) for item in value))


##############################################
# The metaclass and the class-body question

# The mark a node class body carries while it runs. CPython 3.12 inlines
# a comprehension into the body's frame (PEP 709) and, while the
# comprehension's hidden loop variable is live, `frame.f_locals` is a
# plain dict COPY of the namespace rather than the namespace itself; the
# copy still holds this entry, so the body is recognized in either form.
# The metaclass removes it before the class exists.
_BODY_KEY = '__solid_node_body__'
_BODY = object()

# Where a class body's relations accumulate while it runs. The list is
# created ONCE, in __init__, and only ever appended to: inside a PEP 709
# inlined comprehension the frame reports a plain dict COPY of the
# namespace, and the copy holds the same list OBJECT, so an append there
# lands on the real one. Rebinding the key would silently lose it.
_RELATIONS_KEY = '__solid_node_relations__'


class _DeclaringNamespace(dict):
    """The namespace a node class body executes in.

    Its type -- or, during an inlined comprehension, the mark it
    carries -- is what a node constructor looks for on the stack, and
    its `__setitem__` names each declaration as it is assigned, so the
    rest of the body can talk about it by name.
    """

    def __init__(self):
        super().__init__()
        super().__setitem__(_BODY_KEY, _BODY)
        super().__setitem__(_RELATIONS_KEY, [])

    def __setitem__(self, key, value):
        shadowed = self.get(key)
        if shadowed is not None and shadowed is not value:
            _refuse_coordinate_clash(self, key, shadowed, value)
        if isinstance(value, (Declaration, ChildDeclaration,
                              RepeatDeclaration)):
            if isinstance(value, Declaration) and value._name is None:
                value._name = key
            elif not isinstance(value, Declaration):
                value._name = key
        elif getattr(value, '_names_in_body', False) and value._name is None:
            # A relation and a derived coordinate are named here for the
            # same reason a declaration is: an error raised while the
            # body still runs can then say `great` or `relative`, and
            # __set_name__ is too late for that.
            value._name = key
        super().__setitem__(key, value)


def _refuse_coordinate_clash(namespace, key, shadowed, value):
    """A name declared as both a joint and a port in one class body.

    The second assignment would simply replace the first in the
    namespace, leaving one declaration and no sign of the other, so the
    clash is only visible here -- while the body runs -- and is refused
    where it was written.
    """
    if not _is_coordinate(shadowed) or not _is_coordinate(value):
        return
    if _is_joint(shadowed) == _is_joint(value):
        return
    joint, port = ((shadowed, value) if _is_joint(shadowed)
                   else (value, shadowed))
    owner = namespace.get('__qualname__', '<class>')
    raise TypeError(
        f"'{key}' on {owner} is declared twice, as the joint {joint!r} "
        f"and as the port {port!r}. A joint already owns one coordinate, "
        f"which IS a port of that name, so the two cannot share it: "
        f"drop the port, or rename one of them.")


def executing_body():
    """The node class body executing up the stack, or None.

    The namespace itself when the frame is the class statement's own,
    and the plain dict COPY of it inside an inlined comprehension (see
    `_BODY_KEY`) -- the copy shares the relations list, so recording
    through it lands on the real one.
    """
    frame = sys._getframe(1)
    while frame is not None:
        found = frame.f_locals
        if (isinstance(found, _DeclaringNamespace)
                or (type(found) is dict and found.get(_BODY_KEY) is _BODY)):
            return found
        frame = frame.f_back
    return None


def record_relation(relation):
    """Record `relation` on the class body that is executing.

    A relation is a STATEMENT: `power.drives(centre)` written bare is
    recorded here, and assigning its result only additionally names it.
    Called with no node class body executing, it is refused by name --
    there is no instance-time `drives` to mistake it for.
    """
    namespace = executing_body()
    if namespace is None:
        raise TypeError(
            f'{relation!r} was stated with no node class body executing: a '
            f'relation is declared in a class body and is class metadata, '
            f'like a port or a child. Write a.drives(b) in the body of the '
            f'assembly that owns the relation.')
    namespace[_RELATIONS_KEY].append(relation)
    return relation


def in_class_body():
    """Whether a node class body is executing somewhere up the stack.

    The class statement runs its body as a frame whose locals are the
    namespace `NodeMeta.__prepare__` returned, so that namespace on the
    stack is the body, and a body that raised is not on the stack. Inside
    an inlined comprehension the frame reports a copy of the namespace
    instead (see `_BODY_KEY`); the copy carries the mark.
    """
    frame = sys._getframe(1)
    while frame is not None:
        found = frame.f_locals
        if (isinstance(found, _DeclaringNamespace)
                or (type(found) is dict and found.get(_BODY_KEY) is _BODY)):
            return True
        frame = frame.f_back
    return False


class NodeMeta(type):
    """The metaclass of every node class.

    It does two things and nothing else: hands the class statement the
    namespace that marks a body as executing (see `in_class_body`) and
    takes the mark back when the body is done, and names the
    declarations that body assigns. A project that gives a
    node its own metaclass derives it from this one, as `CheckCQEditor`
    does.
    """

    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        return _DeclaringNamespace()

    def __new__(mcs, name, bases, namespace, **kwargs):
        # The body has finished running: the mark has done its job and
        # is not an attribute of the class.
        namespace.pop(_BODY_KEY, None)
        relations = namespace.pop(_RELATIONS_KEY, None)
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if relations:
            # A local import, taken only by a class that carries
            # relations, exactly as `Time.__set_name__` reaches
            # AssemblyNode: no import edge is added for anything else.
            from solid_node.node.assembly import AssemblyNode

            if not issubclass(cls, AssemblyNode):
                raise TypeError(
                    f'{name} states {len(relations)} relation(s) and is not '
                    f'an assembly: a relation is solved at the end of a '
                    f'simulate phase, and only an AssemblyNode has one. '
                    f'Declare the relation on the assembly that owns the '
                    f'coordinates.')
            cls._declared_relations = tuple(relations)
            for relation in relations:
                # The class exists now, so its own ports, joints,
                # drivers and children can be enumerated: an end that
                # belongs to some other class is refused here rather
                # than resolving to a slot nothing ever binds.
                relation.check_declared_on(cls)
        return cls


##############################################
# Enumeration

_children_cache = {}


def declared_children(node_class):
    """Every child declared on `node_class`, by attribute: a
    `ChildDeclaration`, a list of them, or a `RepeatDeclaration`."""
    cached = _children_cache.get(node_class)
    if cached is None:
        found = {}
        for klass in reversed(node_class.__mro__):
            for name, value in vars(klass).items():
                if isinstance(value, (ChildDeclaration, RepeatDeclaration)):
                    found[name] = value
                elif _is_child_list(value):
                    found[name] = list(value)
        cached = _children_cache[node_class] = found
    return cached


def is_declarative(node_class):
    """Whether the class declares anything: parameters or children."""
    return bool(declared_parameters(node_class)
                or declared_children(node_class))


##############################################
# Realization

def resolve_parameters(node_class, kwargs):
    """The resolved value of every declared and derived parameter of
    `node_class` for one instance, from the caller's keyword arguments
    and the declarations' defaults."""
    declared = declared_parameters(node_class)
    owner = node_class.__name__
    settable = [name for name, declaration in declared.items()
                if not declaration.derived]
    for name in kwargs:
        declaration = declared.get(name)
        if declaration is None:
            raise TypeError(
                f"{owner} has no parameter '{name}'; it declares: "
                f"{', '.join(settable) or 'none'}")
        if declaration.derived:
            raise TypeError(
                f"{owner}.{name} is derived from other parameters and cannot "
                f"be supplied; it declares: {', '.join(settable) or 'none'}")
    values = {}
    for name, declaration in declared.items():
        if declaration.derived:
            continue
        supplied = kwargs[name] if name in kwargs else declaration.default
        values[name] = declaration.resolve(supplied, owner)
    for name, declaration in declared.items():
        if declaration.derived:
            values[name] = declaration.evaluate(values)
    return values


def identity_values(node_class, values):
    """The declared (not derived) values, the part of `values` that
    identifies the instance's artifacts."""
    return {name: values[name]
            for name, declaration in declared_parameters(node_class).items()
            if not declaration.derived}


def realize_children(node):
    """Construct `node`'s declared children in declaration order, into
    its instance dict under the declaring attribute, named after it.

    The names are the ones `_link_child` would derive later; deriving
    them here as well means a child answers to its name from the moment
    it exists, and linking is idempotent so nothing changes when it runs.

    `node` itself is handed to each declaration's `realize` as the
    realized PARENT (not merely its class's name, a string, as before
    the declaration-site-joint cycle): a site-declared joint resolves
    its arguments against this exact instance, and a site's callable
    argument is called with it. By the time a later attribute's
    declaration realizes, every EARLIER attribute is already set on
    `node.__dict__` -- this loop's own doing -- which is what a site
    callable may read.
    """
    values = node.__dict__.get('_parameters', {})
    owner = node
    for attribute, declaration in declared_children(type(node)).items():
        if isinstance(declaration, list):
            realized = [item.realize(values, owner) for item in declaration]
        else:
            realized = declaration.realize(values, owner)
        if isinstance(realized, list):
            for index, child in enumerate(realized):
                _name_child(child, f'{attribute}-{index}')
        else:
            _name_child(realized, attribute)
        node.__dict__[attribute] = realized


def _name_child(child, name):
    if not getattr(child, '_explicit_name', False):
        child.name = name


def declared_child_nodes(node):
    """The realized declared children of `node`, flattened in
    declaration order; empty for a class that declares none."""
    found = []
    for attribute in declared_children(type(node)):
        realized = node.__dict__.get(attribute)
        if realized is None:
            continue
        if isinstance(realized, list):
            found.extend(realized)
        else:
            found.append(realized)
    return found


def parse_overrides(node_class, pairs):
    """`--set name=value` words into keyword arguments for `node_class`,
    each parsed by the parameter's declared kind."""
    declared = declared_parameters(node_class)
    settable = [name for name, declaration in declared.items()
                if not declaration.derived]
    overrides = {}
    for pair in pairs or ():
        name, separator, text = pair.partition('=')
        if not separator or not name:
            raise ParameterError(
                f"cannot read {pair!r}: --set takes name=value")
        if not settable:
            raise ParameterError(
                f"{node_class.__name__} declares no parameters, so --set "
                f"{pair} has nothing to set")
        declaration = declared.get(name)
        if declaration is None:
            raise ParameterError(
                f"{node_class.__name__} has no parameter '{name}'; settable: "
                f"{', '.join(settable)}")
        if declaration.derived:
            raise ParameterError(
                f"{node_class.__name__}.{name} is derived from other "
                f"parameters and cannot be set; settable: "
                f"{', '.join(settable)}")
        overrides[name] = declaration.parse(text)
    return overrides
