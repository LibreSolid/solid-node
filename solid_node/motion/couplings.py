# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A law between two coordinates.

One verb, written as a statement in a class body::

    class Movement(AssemblyNode):
        power = TrainArbor(index=0)
        centre = TrainArbor(index=1)

        power.drives(centre, law=going_train)

`drives` states the MECHANICAL direction -- what turns what -- and
nothing else. Which way the framework actually SOLVES it is decided per
run, from whichever end is bound when the owning assembly's simulate
phase ends: forward through the law when the driver is bound, backward
through its inverse when the driven one is. That is what lets wall clock
01 delete `arbor_angles`, which walks its going train BACKWARDS from the
escape wheel because the escapement is where the law is prescribed and
the great wheel is where the power comes in, while Thor's arm reads
forwards from seven root drivers.

The LAW is project code handed in, never looked up. `law=` takes a
callable of the two realized coordinate OWNERS, called once per parent
instance at realization, and returns anything with `forward` and
optionally `inverse` -- `Affine(ratio, offset)` being the one the
framework provides. The framework holds no registry of mechanism
shapes, consults no attribute of a node class to discover a law, and
never learns what a gear is: a class hook was rejected explicitly,
because it would make "what an arbor drives" a property of a class the
framework has to look up, which is the vocabulary this layer exists to
avoid (ADR-089).

A linear formula over coordinates -- `art3.elbow - shoulder`,
`wrist + 2 * tool` -- is itself a coordinate of the class: it reads on
an instance as a bound port slot, it can drive and be driven, and it
solves backwards through exactly one unbound term. Anything that is not
linear is a `law=`.

Module scope imports `solid_node.motion.ports` and nothing else: a
relation relates two ports, so that cost is unavoidable, and everything
from the node package -- the declaring namespace, the child declaration,
the driver declaration, the tree -- is reached inside the method that
needs it, exactly as `Joint` reaches the operations. Importing this
module pulls no CAD backend and no exact stack.
"""

from dataclasses import dataclass

from solid_node.motion.ports import (BoundPort, Port, RotationalPort,
                                     SignalPort, TranslationalPort, bind,
                                     binding_as, declared_ports,
                                     set_coordinate, wiring_binding)
from solid_node.node.phase import current as _current_phase
from solid_node.node.phase import current_enumeration as _current_enumeration


__all__ = ['Affine', 'CouplingError', 'DerivedCoordinate', 'DoublyBound',
           'NotInvertible', 'PrematureRead', 'Relation', 'UnreachedCoordinate',
           'clear_solved', 'declared_derived', 'declared_relations',
           'refuse_reads', 'run_deferred', 'solve_relations']


class CouplingError(ValueError):
    """A relation cannot be resolved or solved."""


class UnreachedCoordinate(CouplingError):
    """A coordinate nothing bound and no relation reached."""


class DoublyBound(CouplingError):
    """Two binders reached one coordinate in one enumeration."""


class NotInvertible(CouplingError):
    """A law was needed backwards and offers no inverse."""


class PrematureRead(CouplingError):
    """A coordinate a relation, a derived formula or a wiring binds was
    read while unbound, during the simulate phase of the class that
    reads it -- because that phase runs BEFORE the binder, whichever
    class states it, is solved (`whole-tree-fixpoint`)."""




def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_zero(value):
    return _is_number(value) and value == 0


def _is_one(value):
    return _is_number(value) and value == 1


def _coordinate_of(value):
    """The port `value` offers as a coordinate: itself when it is a port
    declaration, its `coordinate` when it owns one (a joint, a derived
    coordinate), else None. The same duck-typed seam `declared_ports`
    uses, restated here rather than closed into an import cycle."""
    if isinstance(value, Port):
        return value
    owned = getattr(value, 'coordinate', None)
    return owned if isinstance(owned, Port) else None


def _coordinates_of(value):
    """The coordinates `value` owns when it owns SEVERAL -- a `Free`'s
    six, by the dotted names they carry -- and None otherwise.

    The companion of `_coordinate_of`: that one answers "which single
    coordinate is this", and a joint that is several has to be refused
    by name rather than stood in for. Duck-typed on `coordinates` for
    the reason `_coordinate_of` is duck-typed on `coordinate`.
    """
    owned = getattr(value, 'coordinates', None)
    if (isinstance(owned, dict) and len(owned) > 1
            and all(isinstance(port, Port) for port in owned.values())):
        return owned
    return None


def _refuse_several_coordinates(joint, written, detail=''):
    owned = ', '.join(joint.coordinates)
    first = next(iter(joint.coordinates))
    return TypeError(
        f"'{written}' names the joint '{joint.name}', which owns "
        f"{len(joint.coordinates)} coordinates and stands for none of "
        f"them{detail}. A relation has one end; it owns {owned}, so name "
        f"one of them -- {first}.")


##############################################
# The law

@dataclass(frozen=True)
class Affine:
    """`driven = ratio * driver + offset`, and its algebraic inverse.

    Ordinary arithmetic, deliberately: a `DriverToken` or `$t` for the
    operand builds the wire expression solid2 builds, and a number gives
    a number. A ratio of one and an offset of zero are skipped rather
    than multiplied and added, so an identity never publishes `(x * 1)`.

    Invertible unless the ratio is a NUMBER equal to zero: a symbolic
    ratio is taken as invertible, because the division is as well-formed
    as the multiplication and refusing it would mean deciding a value
    the framework does not have.
    """

    ratio: object = 1
    offset: object = 0

    def forward(self, driver):
        value = driver if _is_one(self.ratio) else self.ratio * driver
        return value if _is_zero(self.offset) else value + self.offset

    def inverse(self, driven):
        value = driven if _is_zero(self.offset) else driven - self.offset
        return value if _is_one(self.ratio) else value / self.ratio

    @property
    def invertible(self):
        return not _is_zero(self.ratio)

    def __repr__(self):
        return f'Affine(ratio={self.ratio!r}, offset={self.offset!r})'


class ForwardOnly:
    """A plain function returned by a `law=` callable: a forward face
    and no way back."""

    invertible = False

    def __init__(self, function):
        self.forward = function
        self.function = function

    def __repr__(self):
        named = getattr(self.function, '__name__', self.function)
        return f'<forward-only law {named!r}>'


def as_law(value, relation):
    """`value` as a law, or a refusal naming the relation and what the
    callable returned."""
    if callable(getattr(value, 'forward', None)):
        return value
    if callable(value):
        return ForwardOnly(value)
    raise CouplingError(
        f'{relation}: the law callable returned {value!r}, which is not a '
        f'law. A law is an object with a callable forward(x), and '
        f'optionally an inverse(y) -- Affine(ratio, offset) is one -- or '
        f'a plain function, taken as forward-only.')


def invertible(law):
    stated = getattr(law, 'invertible', None)
    if stated is not None:
        return bool(stated)
    return callable(getattr(law, 'inverse', None))


##############################################
# Coordinate references

class CoordinateRef:
    """One end of a relation, before an instance resolves it.

    Carries the verb and the linear algebra of a derived coordinate; the
    kinds differ only in how they find their coordinate on a realized
    instance and which node OWNS it.
    """

    # (kind, identity...) -- what makes two references to one coordinate
    # the same term of a formula.
    def key(self):
        raise NotImplementedError

    def __eq__(self, other):
        return isinstance(other, CoordinateRef) and self.key() == other.key()

    def __hash__(self):
        return hash(self.key())

    ##############################################
    # The verb

    def drives(self, other, ratio=None, offset=None, law=None):
        return relate(self, other, ratio, offset, law)

    ##############################################
    # What the reference names

    def declaration(self):
        """The port, joint or derived coordinate this end names, as far
        as the classes alone can say."""
        raise NotImplementedError

    def coordinate(self):
        declared = self.declaration()
        return _coordinate_of(declared)

    @property
    def domain(self):
        found = self.coordinate()
        return None if found is None else found.domain

    @property
    def unit(self):
        found = self.coordinate()
        return None if found is None else found.unit

    def described(self):
        raise NotImplementedError

    def check(self, role):
        """Whatever the classes alone decide, refused where it was
        written."""

    def check_declared_on(self, owner, relation):
        """Refused when the class being created does not declare this
        end. Checked when the class exists, which is the first moment
        its declarations can be enumerated."""

    def resolve(self, instance):
        raise NotImplementedError

    ##############################################
    # The linear algebra of a derived coordinate

    def terms(self):
        return {self: 1}, 0

    def __and__(self, other):
        return group_with(self, other)

    def __add__(self, other):
        return _combine(self, other, 1)

    def __radd__(self, other):
        return _combine(self, other, 1)

    def __sub__(self, other):
        return _combine(self, other, -1)

    def __rsub__(self, other):
        return _combine(-self, other, 1)

    def __neg__(self):
        return _scaled(self, -1)

    def __mul__(self, other):
        return _scaled(self, _coefficient(self, other, '*'))

    def __rmul__(self, other):
        return _scaled(self, _coefficient(self, other, '*'))

    def __truediv__(self, other):
        return _scaled(self, 1 / _coefficient(self, other, '/'))

    def __float__(self):
        raise TypeError(
            f'{self.described()} is a coordinate, not a number: a class body '
            f'names the place a value will be, and a function of that place '
            f'is not linear. Write the relation with law=.')


class OwnRef(CoordinateRef):
    """A port or a joint declared on the class stating the relation."""

    def __init__(self, declared):
        self.declared = declared

    def key(self):
        return ('own', id(self.declared))

    def declaration(self):
        return self.declared

    def described(self):
        return _declaration_name(self.declared)

    def check_declared_on(self, owner, relation):
        from solid_node.motion.joints import declared_joints

        ours = list(declared_ports(owner).values())
        ours.extend(declared_joints(owner).values())
        if any(self.declared is mine for mine in ours):
            return
        elsewhere = getattr(self.declared, 'owner', None)
        belongs = (f'{elsewhere.__name__} declares it'
                   if elsewhere is not None
                   else 'it is declared on no class here')
        raise TypeError(
            f"{owner.__name__}: the coordinate '{self.described()}' named "
            f"by the relation {relation.described()} is not declared on "
            f"{owner.__name__} -- {belongs}. A relation relates this "
            f"class's own coordinates and those of the children it "
            f"declares; reach another node's coordinate by path.")

    def resolve(self, instance):
        return ResolvedEnd(instance, self.declared, self)

    def __repr__(self):
        return f'<coordinate {self.described()}>'


class DriverRef(CoordinateRef):
    """A `Driver` declaration: a source only."""

    def __init__(self, declared):
        self.declared = declared

    def key(self):
        return ('driver', id(self.declared))

    def declaration(self):
        return self.declared

    def coordinate(self):
        return None

    def described(self):
        return _declaration_name(self.declared)

    def check(self, role):
        if role == 'driven':
            raise TypeError(
                f"driver '{self.described()}' cannot be the driven end of a "
                f"relation: a driver's value belongs to the bound snapshot, "
                f"and is set with set_state({self.described()}=...). State "
                f"the relation the other way round.")

    def check_declared_on(self, owner, relation):
        from solid_node.node.qualified import declared_drivers_of

        if any(self.declared is mine
               for mine in declared_drivers_of(owner).values()):
            return
        raise TypeError(
            f"{owner.__name__}: the driver '{self.described()}' named by "
            f"the relation {relation.described()} is not declared on "
            f"{owner.__name__}. A driver is addressed by the qualified id "
            f"its position in the tree gives it, so a relation from one is "
            f"stated on the class that declares it.")

    def resolve(self, instance):
        return ResolvedEnd(instance, self.declared, self)

    def __repr__(self):
        return f'<driver {self.described()}>'


class PathRef(CoordinateRef):
    """A child declaration, or an attribute path reached through one.

    `centre`, `anchor.turn`, `shoulder.art2.art3.wrist`: a place in the
    tree rather than a value. Every segment is checked against the class
    the previous segment names, at class definition, because the classes
    are all known there.
    """

    def __init__(self, root, segments, terminal):
        self.root = root
        self.segments = tuple(segments)
        self.terminal = terminal

    def key(self):
        return ('path', id(self.root), self.segments)

    @property
    def written(self):
        return '.'.join((self.root._name or self.root.node_class.__name__,)
                        + self.segments)

    def described(self):
        return self.written

    def declaration(self):
        if _coordinate_of(self.terminal) is not None:
            return self.terminal
        if _coordinates_of(self.terminal) is not None:
            # A path that STOPS on a joint owning several: `chassis.pose`.
            raise _refuse_several_coordinates(self.terminal, self.written)
        return _the_one_joint(self.terminal, self.written)

    def check(self, role):
        if self.root._name is None:
            raise TypeError(
                f'a declaration held in a list is named <attribute>-index '
                f'and names one child per entry, so it cannot be an end of '
                f'a relation. Hold the '
                f'{self.root.node_class.__name__} on its own attribute, or '
                f'state the relation inside it.')
        # A node end means its one joint, and a class with none or
        # several is refused here, naming what it does declare.
        self.declaration()

    def check_declared_on(self, owner, relation):
        from solid_node.node.declarative import declared_children

        declared = declared_children(owner).get(self.root._name)
        if declared is self.root:
            return
        raise TypeError(
            f"{owner.__name__}: '{self.root._name}', the first segment of "
            f"{self.written} in the relation {relation.described()}, is not "
            f"a child {owner.__name__} declares. A path is walked from the "
            f"instance stating the relation.")

    def __getattr__(self, attribute):
        if attribute.startswith('_'):
            raise AttributeError(attribute)
        from solid_node.node.declarative import ChildDeclaration, RepeatDeclaration

        owned = _coordinates_of(self.terminal)
        if owned is not None:
            # A joint owning several DOES have parts, and each of them
            # is one segment of the path: `chassis.pose.roll`.
            found = owned.get(f'{self.terminal.name}.{attribute}')
            if found is None:
                raise _refuse_several_coordinates(
                    self.terminal, self.written,
                    f", and no coordinate of it is called '{attribute}'")
            return PathRef(self.root, self.segments + (attribute,), found)
        if not isinstance(self.terminal, ChildDeclaration):
            raise TypeError(
                f"cannot read '{attribute}' through {self.written}: that "
                f"path already names a coordinate, and a coordinate has no "
                f"parts.")
        found = read_through(self.terminal.node_class, attribute,
                             f'{self.written}.{attribute}')
        if isinstance(found, RepeatDeclaration):
            # The FIRST repeat this path steps onto: a broadcast from
            # here on, not a refusal (ADR-095's own relaxation, extended
            # to a repeated segment).
            return BroadcastRef(self.root, self.segments + (attribute,),
                               found, found)
        return PathRef(self.root, self.segments + (attribute,), found)

    def resolve(self, instance):
        node = self._walk(instance)
        declared = self.declaration()
        return ResolvedEnd(node, declared, self)

    def _walk(self, instance):
        """The realized node that OWNS this end's coordinate: the
        descendant declaring the named port or joint, or the named node
        itself when the path ends on a node."""
        from solid_node.node.declarative import ChildDeclaration

        segments = list(self.segments)
        coordinate = _coordinate_of(self.terminal)
        if segments and coordinate is not None:
            # A coordinate occupies as many TRAILING segments as the
            # name it is reported under has parts: one for a plain port
            # or a joint that owns one, two for `pose.roll`.
            del segments[-(str(coordinate.name).count('.') + 1):]
        node = self._step(instance, self.root._name, self.written)
        for segment in segments:
            node = self._step(node, segment, self.written)
        return node

    def _step(self, node, attribute, written):
        try:
            found = getattr(node, attribute)
        except AttributeError as failure:
            raise CouplingError(
                f"{type(node).__name__} '{getattr(node, 'name', node)}' has "
                f"no realized '{attribute}', so the path {written} does not "
                f"resolve on this instance ({failure}). A path is resolved "
                f"against the children the instance actually realized.")
        if isinstance(found, (list, tuple)):
            raise CouplingError(
                f"'{attribute}' of {type(node).__name__} is {len(found)} "
                f"children, so the path {written} names no single "
                f"coordinate. State the relation inside the repeated class.")
        return found

    def __repr__(self):
        return f'<path {self.written}>'


class BroadcastRef(PathRef):
    """A path that passes through ONE repeated child declaration: the
    same coordinate of every copy the repeat realizes, in copy order.

    Shares `PathRef`'s shape -- `(root, segments, terminal)` -- and most
    of its behaviour: class definition validates a `BroadcastRef`
    exactly as a `PathRef`, because the CLASSES are all known there and
    the repeat changes only how many REALIZED instances the path lands
    on. `repeat` is the `RepeatDeclaration` this path passes through,
    kept for the messages that name it (the source refusal, the
    two-repeat refusal) -- not the position `design.md` describes in the
    abstract, which this carries as the object itself.
    """

    def __init__(self, root, segments, terminal, repeat):
        super().__init__(root, segments, terminal)
        self.repeat = repeat

    def key(self):
        return ('broadcast', id(self.root), self.segments)

    def check(self, role):
        if role == 'driver':
            raise TypeError(
                f"'{self.written}' passes through the repeated declaration "
                f"'{self.repeat._name}' of {self.repeat.node_class.__name__} "
                f"(count={self.repeat.count!r}), so it cannot be the SOURCE "
                f"of a relation: a relation's source is one value, and the "
                f"copies hold one each. Bind the source from a coordinate "
                f"the parent holds, or state the relation inside "
                f"{self.repeat.node_class.__name__}.")
        super().check(role)

    def terms(self):
        raise TypeError(
            f"'{self.written}' passes through the repeated declaration "
            f"'{self.repeat._name}' of {self.repeat.node_class.__name__}, so "
            f"it cannot be a term of a derived coordinate: a formula has "
            f"one value per term, and the copies hold one each. Write the "
            f"relation with law=.")

    def __getattr__(self, attribute):
        if attribute.startswith('_'):
            raise AttributeError(attribute)
        from solid_node.node.declarative import ChildDeclaration, RepeatDeclaration

        owned = _coordinates_of(self.terminal)
        if owned is not None:
            found = owned.get(f'{self.terminal.name}.{attribute}')
            if found is None:
                raise _refuse_several_coordinates(
                    self.terminal, self.written,
                    f", and no coordinate of it is called '{attribute}'")
            return BroadcastRef(self.root, self.segments + (attribute,),
                               found, self.repeat)
        if not isinstance(self.terminal, (ChildDeclaration, RepeatDeclaration)):
            raise TypeError(
                f"cannot read '{attribute}' through {self.written}: that "
                f"path already names a coordinate, and a coordinate has no "
                f"parts.")
        node_class = self.terminal.node_class
        found = read_through(node_class, attribute,
                             f'{self.written}.{attribute}')
        if isinstance(found, RepeatDeclaration):
            raise TypeError(
                f"'{self.written}.{attribute}' passes through TWO repeated "
                f"declarations -- '{self.repeat._name}' of "
                f"{self.repeat.node_class.__name__} and '{found._name}' of "
                f"{found.node_class.__name__} -- and a broadcast fans out "
                f"over ONE repeat. State the relation inside the more "
                f"deeply repeated class instead.")
        return BroadcastRef(self.root, self.segments + (attribute,), found,
                           self.repeat)

    def resolve_all(self, instance):
        """A `ResolvedEnd` per realized copy, in copy order -- empty for
        a repeat that realized none."""
        declared = self.declaration()
        return [ResolvedEnd(node, declared, self)
                for node in self._walk_copies(instance)]

    def _walk_copies(self, instance):
        segments = list(self.segments)
        coordinate = _coordinate_of(self.terminal)
        if segments and coordinate is not None:
            del segments[-(str(coordinate.name).count('.') + 1):]
        nodes = [instance]
        for attribute in [self.root._name] + segments:
            expanded = []
            for node in nodes:
                found = self._raw_step(node, attribute)
                if isinstance(found, (list, tuple)):
                    # The repeated segment: one node becomes n.
                    expanded.extend(found)
                else:
                    expanded.append(found)
            nodes = expanded
        return nodes

    def _raw_step(self, node, attribute):
        try:
            return getattr(node, attribute)
        except AttributeError as failure:
            raise CouplingError(
                f"{type(node).__name__} '{getattr(node, 'name', node)}' has "
                f"no realized '{attribute}', so the path {self.written} "
                f"does not resolve on this instance ({failure}). A path is "
                f"resolved against the children the instance actually "
                f"realized.") from None

    def copy_nodes(self, instance):
        """The nodes the REPEATED SEGMENT ITSELF realized, in copy order
        -- what a `RelationRecord`'s `copy` names, whether or not this
        path continues past the repeat to reach its coordinate
        (`legs.femur.lift`'s copy is the LEG, not the femur: design.md
        section 5, the correction to ADR-096's `copy = driven.node`)."""
        return self._walk_copy_nodes(instance)

    def _walk_copy_nodes(self, instance):
        segments = list(self.segments)
        coordinate = _coordinate_of(self.terminal)
        if segments and coordinate is not None:
            del segments[-(str(coordinate.name).count('.') + 1):]
        nodes = [instance]
        copy_nodes = None
        for attribute in [self.root._name] + segments:
            expanded = []
            for node in nodes:
                found = self._raw_step(node, attribute)
                if isinstance(found, (list, tuple)):
                    expanded.extend(found)
                else:
                    expanded.append(found)
            if copy_nodes is None and len(expanded) != len(nodes):
                # The one repeated segment this path passes through
                # (design.md: at most one): the nodes right after THIS
                # expansion are the copies, whatever further segments
                # the path still has to walk from here.
                copy_nodes = list(expanded)
            nodes = expanded
        return nodes if copy_nodes is None else copy_nodes

    def __repr__(self):
        return f'<broadcast {self.written}>'


##############################################
# Groups: several coordinates named as one end

class Coordinates:
    """Several coordinates named as one end of a relation, built by `&`
    in a class body, in the order written (design.md section 2, "The two
    objects").

    Holds the RAW operands, not yet converted to `CoordinateRef`s: the
    ROLE (driver or driven) is not known until `drives` is called, and
    the same member is checked differently as a source and as a driven
    end -- `coordinate_ref` does that conversion, late, once `drives`
    supplies the role. Never imported by a project and not exported.
    """

    def __init__(self, *operands):
        self.operands = tuple(operands)

    def __and__(self, other):
        return group_with(self, other)

    def drives(self, other, ratio=None, offset=None, law=None):
        return relate(self, other, ratio, offset, law)

    def _refuse_as_formula_term(self, *_args, **_kwargs):
        raise TypeError(
            f'{self!r} cannot be a term of a derived coordinate: a formula '
            f'has one value per term, and a group names several. Write the '
            f'relation with law=.')

    __add__ = __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = \
        __truediv__ = _refuse_as_formula_term

    def __repr__(self):
        return f"<group {' & '.join(repr(o) for o in self.operands)}>"


def _is_group_member(value):
    """Whatever `&` may join into a group: any raw declaration kind
    `coordinate_ref` would otherwise accept -- the per-kind and
    per-role refusals (a repeated source, a driver as a driven end, a
    node of the wrong joint count) are left to `coordinate_ref` and
    `check(role)`, once the role is known. Only a value with no coordinate
    reading at all -- a number, text, an unrelated object -- is refused
    here, immediately, naming the `&`."""
    from solid_node.node.declarative import ChildDeclaration, RepeatDeclaration
    from solid_node.node.qualified import DriverDeclaration

    if isinstance(value, (CoordinateRef, Coordinates, ChildDeclaration,
                         RepeatDeclaration, DriverDeclaration)):
        return True
    return _coordinate_of(value) is not None or _coordinates_of(value) is not None


def group_with(left, right):
    """`left & right`: the operator behind every declaration that
    carries `drives` (design.md section 2). Builds or extends a
    `Coordinates`, flat and left-associative -- `x & y & z` is one group
    of three, never a nested pair -- or raises the missing-parentheses
    refusal when the right operand is already a stated relation, because
    `.drives` binds tighter than `&`."""
    if isinstance(right, Relation):
        raise TypeError(
            f'{right.described()}: the parentheses are missing. `&` binds '
            f'looser than `.drives`, so `a & b.drives(c)` states the '
            f'ONE-source relation b.drives(c) first, and then asks for '
            f'`{left!r} & <that relation>`. Write `(a & b).drives(c, ...)`.')
    if not _is_group_member(right):
        raise TypeError(
            f'{right!r} is not a coordinate, so it cannot join a group with '
            f'&: a group is a group of coordinates.')
    left_operands = left.operands if isinstance(left, Coordinates) else (left,)
    right_operands = (right.operands if isinstance(right, Coordinates)
                      else (right,))
    return Coordinates(*left_operands, *right_operands)


def _group_operands(value):
    return value.operands if isinstance(value, Coordinates) else value


def _end_group(value, role):
    """`coordinate_ref`'s conversion of a `Coordinates` or a literal
    tuple into an `EndGroup`: the structural checks that do not depend
    on role (size, nesting, duplication), then a per-member conversion
    with the role now known."""
    operands = _group_operands(value)
    if (len(operands) < 2
            or any(isinstance(item, (tuple, Coordinates)) for item in operands)):
        raise TypeError(
            'a group names two coordinates or more, and ends are named one '
            'by one: a group cannot be empty, hold a single coordinate, or '
            'hold another group. Name a single coordinate without &, or '
            'flatten the group into one & chain.')
    refs = []
    seen = {}
    for operand in operands:
        ref = coordinate_ref(operand, role)
        key = ref.key()
        if key in seen:
            raise TypeError(
                f'{ref.described()} is named twice in one group: a '
                f'coordinate is named once in a group.')
        seen[key] = ref
        refs.append(ref)
    return EndGroup(refs)


class EndGroup(CoordinateRef):
    """Several coordinates named as ONE end of a relation -- what
    `coordinate_ref` builds from a `Coordinates` (the `&` group) or a
    literal tuple (the driven side's `(a, b, c)`), late, because the
    role is not known until `drives` is called (design.md section 2,
    "The two objects")."""

    def __init__(self, refs):
        self.refs = tuple(refs)

    def key(self):
        return ('group', tuple(ref.key() for ref in self.refs))

    def described(self):
        return f"({', '.join(ref.described() for ref in self.refs)})"

    def declaration(self):
        raise TypeError(
            f'{self.described()} names several coordinates: it has no one '
            f'declaration. Read each member of the group instead.')

    def check(self, role):
        for ref in self.refs:
            ref.check(role)
        if role == 'driven':
            _check_driven_fanout(self.refs)

    def check_declared_on(self, owner, relation):
        for ref in self.refs:
            ref.check_declared_on(owner, relation)

    def resolve(self, instance):
        return tuple(ref.resolve(instance) for ref in self.refs)

    def resolve_all(self, instance):
        """Per-copy tuples of this group's `ResolvedEnd`s -- valid only
        once every member is confirmed a broadcast over the SAME repeat
        (`check('driven')`, at class definition)."""
        per_member = [ref.resolve_all(instance) for ref in self.refs]
        return list(zip(*per_member))

    def copy_nodes(self, instance):
        return self.refs[0].copy_nodes(instance)

    def __repr__(self):
        return f'<group {self.described()}>'


def _check_driven_fanout(refs):
    """Every driven end that is a broadcast SHALL fan out over the SAME
    repeated segment as every other; a driven group mixing a broadcast
    with a plain end, or two different repeats, is refused at class
    definition naming both paths (design.md section 5)."""
    broadcasts = [ref for ref in refs if isinstance(ref, BroadcastRef)]
    if not broadcasts:
        return
    if len(broadcasts) != len(refs):
        plain = next(ref for ref in refs if not isinstance(ref, BroadcastRef))
        raise TypeError(
            f"the driven ends of a relation fan out over ONE repeat "
            f"together: '{broadcasts[0].written}' passes through the "
            f"repeated declaration '{broadcasts[0].repeat._name}', and "
            f"'{plain.described()}' does not. Mix no broadcast with an end "
            f"that is not one; state the relation inside the repeated "
            f"class, or drop the plain end from the group.")
    first = broadcasts[0]
    first_site = (id(first.root), id(first.repeat))
    # Identity of the REPEAT OBJECT alone is not enough: two children of
    # one reused class (`left = Side()`, `right = Side()`) share the one
    # `RepeatDeclaration` their shared class declares, yet realize two
    # unrelated sets of copies -- the ROOT each path starts from is what
    # tells them apart.
    for other in broadcasts[1:]:
        if (id(other.root), id(other.repeat)) != first_site:
            raise TypeError(
                f"the driven ends of a relation fan out over ONE repeat "
                f"together: '{first.written}' passes through "
                f"'{first.repeat._name}' and '{other.written}' through "
                f"'{other.repeat._name}' -- two different repeated "
                f"segments. State the relation inside the more deeply "
                f"repeated class, or split it into two relations.")


def _end_refs(ref):
    """The individual `CoordinateRef`s of one end, in written order --
    the group's members, or the ref itself when it names one
    coordinate."""
    return ref.refs if isinstance(ref, EndGroup) else (ref,)


def _is_broadcast(ref):
    """Whether this end -- bare or grouped -- fans out over a repeat.
    A driven group's members are already confirmed to share ONE repeat
    by `_check_driven_fanout`, so testing the first is enough."""
    return isinstance(ref, BroadcastRef) or (
        isinstance(ref, EndGroup)
        and any(isinstance(member, BroadcastRef) for member in ref.refs))


def _resolve_ends(ref, instance):
    """This end's tuple of `ResolvedEnd`, for an ORDINARY (non-broadcast)
    relation -- one member for a bare end, several in written order for
    a group."""
    return tuple(member.resolve(instance) for member in _end_refs(ref))


def _resolve_ends_per_copy(ref, instance):
    """This end's per-copy `(copy_node, driven_ends)` pairs, in copy
    order, for a BROADCAST end -- bare or grouped."""
    members = _end_refs(ref)
    per_member = [member.resolve_all(instance) for member in members]
    copy_nodes = members[0].copy_nodes(instance)
    return list(zip(copy_nodes, zip(*per_member)))


def _law_argument(ends):
    """What a `law=` callable is handed for one end: the realized owner
    of the one coordinate it names, or the TUPLE of owners in written
    order when it names several (couplings spec, "The law of a relation
    is an affine pair, or project code passed in")."""
    if len(ends) == 1:
        return ends[0].node
    return tuple(end.node for end in ends)


def _refuse_shared_coordinate(driver_ref, driven_ref):
    """A coordinate named on BOTH sides of a relation naming several
    ends is refused (proposal.md decision (c)): checked only when either
    end is several, because a one-to-one `a.drives(a)` is untouched by
    this cycle."""
    driver_keys = {ref.key(): ref for ref in _end_refs(driver_ref)}
    for ref in _end_refs(driven_ref):
        if ref.key() in driver_keys:
            raise TypeError(
                f'{ref.described()} is named as both a source and a driven '
                f'end of one relation: a coordinate is a source or a driven '
                f'end of one relation, not both.')


def _the_one_joint(declaration, written):
    """The one joint of a child declaration's class, or the refusal that
    names what it does declare."""
    from solid_node.motion.joints import declared_joints

    node_class = declaration.node_class
    joints = declared_joints(node_class)
    if len(joints) == 1:
        only = next(iter(joints.values()))
        if _coordinates_of(only) is None:
            return only
        # The node stands for its one joint, and that joint stands for
        # no single coordinate. Without this the walk would pass
        # `len(joints) == 1` and return a declaration with no
        # coordinate: a wrong pose rather than an error.
        raise _refuse_several_coordinates(
            only, written,
            f', and it is the only joint {node_class.__name__} declares')
    declares = ', '.join(sorted(joints)) or 'none'
    raise TypeError(
        f"'{written}' names {node_class.__name__}, whose class declares "
        f"{len(joints)} joints ({declares}), so it does not stand for one "
        f"coordinate. A node end means the node's ONE joint; name the "
        f"coordinate instead.")


def read_through(node_class, attribute, written):
    """What reading `attribute` off `node_class` in a class body means.

    The narrow relaxation of the sideways read (ADR-061, extended by
    ADR-089): a port, a joint, a derived coordinate or another child
    declaration names a PLACE in the tree, which a class body may name;
    a parameter is a VALUE belonging to a realized instance, and stays
    refused with the advice it has always carried.
    """
    from solid_node.node.declarative import (ChildDeclaration,
                                             RepeatDeclaration,
                                             SidewaysReadError)
    from solid_node.node.qualified import DriverDeclaration

    found = getattr(node_class, attribute, None)
    if found is not None:
        if _coordinate_of(found) is not None:
            return found
        if _coordinates_of(found) is not None:
            # A joint owning several is a PLACE too: the path steps into
            # it for one of its coordinates, and stopping on it is
            # refused by `PathRef` with the joint's own name.
            return found
        if isinstance(found, ChildDeclaration):
            return found
        if isinstance(found, RepeatDeclaration):
            # A repeated child is a PLACE too, exactly like a plain one:
            # the coordinate it names is the same one of every copy,
            # which is what makes the path a BROADCAST. The caller (a
            # `PathRef`/`BroadcastRef` step, or a bare read off the
            # repeat) is what turns this into one.
            return found
        if _is_declaration_list(found):
            raise TypeError(
                f"'{written}' reaches a list-held child: {node_class.__name__}."
                f"{attribute} holds {len(found)} children, each with its "
                f"own arguments -- named '{attribute}-0', '{attribute}-1', "
                f"and so on -- and a relation names ONE of them, not the "
                f"list. They are named one by one; a relation cannot reach "
                f"all of them through this path.")
        if isinstance(found, DriverDeclaration):
            raise SidewaysReadError(
                f"cannot read the driver '{attribute}' off the "
                f"{node_class.__name__} declaration ({written}): a driver is "
                f"addressed by the qualified id its position in the tree "
                f"gives it, and a second address for one value is what that "
                f"qualification prevents. State "
                f"{attribute}.drives(<coordinate>) on the class declaring "
                f"the driver.")
    declares = _declared_places(node_class)
    if found is None:
        raise SidewaysReadError(
            f"'{written}' names nothing: {node_class.__name__} declares no "
            f"port, joint or child called '{attribute}'. A path reference "
            f"is checked against the classes where it is written, so this "
            f"is a misspelling, not a runtime surprise. "
            f"{node_class.__name__} declares: {declares}.")
    raise SidewaysReadError(
        f"cannot read '{attribute}' off the {node_class.__name__} "
        f"declaration ({written}): a sibling's parameter is not a value in "
        f"a class body; declare the shared parameter on this class and pass "
        f"it to both children. {node_class.__name__} declares: {declares}.")


def _is_declaration_list(value):
    from solid_node.node.declarative import ChildDeclaration

    return (isinstance(value, list) and value
            and all(isinstance(item, ChildDeclaration) for item in value))


def _declared_places(node_class):
    from solid_node.node.declarative import declared_children

    names = sorted(set(declared_ports(node_class))
                   | set(declared_children(node_class)))
    return ', '.join(names) or 'no port, joint or child'


def _declaration_name(declared):
    name = getattr(declared, 'name', None) or getattr(declared, '_name', None)
    if name:
        return name
    return _named_in_body(declared) or repr(declared)


def _named_in_body(value):
    """The name a class body has already given `value`, found in the
    namespace that is executing.

    A declaration is named by `__set_name__` when the class is created,
    which is too late for an error raised while the body still runs; the
    namespace has the name from the moment of assignment, so an error
    about `wrist * tool` can say `wrist` and `tool`.
    """
    from solid_node.node.declarative import executing_body

    namespace = executing_body()
    if namespace is None:
        return None
    for key, held in namespace.items():
        if held is value:
            return key
    return None


##############################################
# Derived coordinates

_PORT_KINDS = {
    'rotational': RotationalPort,
    'translational': TranslationalPort,
    'signal': SignalPort,
}


def _coefficient(ref, other, symbol):
    if not isinstance(other, CoordinateRef) and _coordinate_of(other):
        other = OwnRef(other)
    if isinstance(other, CoordinateRef):
        raise TypeError(
            f"cannot multiply or divide two coordinates "
            f"({ref.described()} {symbol} {other.described()}): a derived "
            f"coordinate is a LINEAR formula, and a product of two "
            f"coordinates is not one. Write the relation with law=.")
    if _is_number(other):
        return other
    from solid_node.parameters import Expression

    if isinstance(other, Expression):
        return other
    raise TypeError(
        f"cannot combine {ref.described()} with {other!r} using {symbol}: a "
        f"derived coordinate is a linear formula over coordinates, scaled by "
        f"a number or a declared parameter. Write the relation with law=.")


def _terms_of(operand):
    if not isinstance(operand, CoordinateRef) and _coordinate_of(operand):
        operand = OwnRef(operand)
    if isinstance(operand, CoordinateRef):
        return operand.terms()
    if _is_number(operand):
        return {}, operand
    from solid_node.parameters import Expression

    if isinstance(operand, Expression):
        return {}, operand
    raise TypeError(
        f'{operand!r} is not a coordinate, a number or a declared '
        f'parameter, so it cannot be a term of a derived coordinate. Write '
        f'the relation with law=.')


def _combine(ref, other, sign):
    left_terms, left_constant = ref.terms()
    right_terms, right_constant = _terms_of(other)
    terms = dict(left_terms)
    for term, coefficient in right_terms.items():
        merged = terms.get(term, 0) + sign * coefficient
        terms[term] = merged
    constant = left_constant + sign * right_constant
    return DerivedCoordinate(terms, constant)


def _scaled(ref, factor):
    terms, constant = ref.terms()
    return DerivedCoordinate(
        {term: coefficient * factor for term, coefficient in terms.items()},
        constant * factor)


class DerivedCoordinate(CoordinateRef):
    """A linear formula over coordinates, which IS a coordinate.

    A mapping from reference to coefficient plus a constant, rather than
    an expression tree: that is what makes the backward solve exact and
    cheap, and it is the shape MuJoCo writes as a `tendon/fixed`. It
    reads on an instance as a bound port slot in the same `_port_values`
    dict the class's ports live in, and `declared_ports` reports it
    beside them.
    """

    # The declaring namespace names one as it names a declaration, so
    # an error raised while the body still runs can say `relative`.
    _names_in_body = True
    _name = None
    owner = None

    def __init__(self, terms, constant):
        self.terms_map = terms
        self.constant = constant
        self._domain, self._unit = _shared_domain(terms)
        kind = _PORT_KINDS.get(self._domain, SignalPort)
        self.coordinate = kind(unit=self._unit)
        # A slot key of its own before anything names it: a formula
        # written straight into a relation -- `(a - b).drives(c)` -- is
        # never assigned, and two such formulas on one class would
        # otherwise share the one slot a nameless port answers to.
        self.coordinate.name = f'_derived_{id(self):x}'

    ##############################################
    # Declaration

    def key(self):
        return ('derived', id(self))

    @property
    def domain(self):
        return self._domain

    @property
    def unit(self):
        return self._unit

    def declaration(self):
        return self

    def described(self):
        return (self._name or _named_in_body(self)
                or self.written)

    @property
    def written(self):
        parts = []
        for term, coefficient in self.terms_map.items():
            factor = '' if _is_one(coefficient) else f'{coefficient!r} * '
            parts.append(f'{factor}{term.described()}')
        formula = ' + '.join(parts) or '0'
        if not _is_zero(self.constant):
            formula = f'{formula} + {self.constant!r}'
        return formula

    def terms(self):
        # FLATTENED into the base coordinates, not held as one term of
        # its own: `left = wrist + 2 * tool` builds the intermediate
        # `2 * tool` before anything names it, and an intermediate no
        # class declares would be a term nothing ever solves.
        return dict(self.terms_map), self.constant

    def __set_name__(self, owner, name):
        self._name = name
        self.owner = owner
        self.coordinate.name = name
        self.coordinate.owner = owner

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self.coordinate.__get__(instance)

    def __set__(self, instance, value):
        raise AttributeError(
            f"derived coordinate '{self._name}' of "
            f"{type(instance).__name__} cannot be assigned: it is the "
            f"formula {self.written}, solved from its terms or from the "
            f"relation that drives it.")

    def resolve(self, instance):
        return ResolvedEnd(instance, self, self)

    def __repr__(self):
        return f'<derived coordinate {self._name or ""}: {self.written}>'

    ##############################################
    # Solving

    def slot_of(self, instance):
        return self.coordinate.__get__(instance)

    def resolved_terms(self, instance):
        """`[(ResolvedEnd, coefficient)]` for this instance."""
        from solid_node.parameters import evaluate

        values = instance.__dict__.get('_parameters', {})
        resolved = []
        for term, coefficient in self.terms_map.items():
            resolved.append((term.resolve(instance),
                             evaluate(coefficient, values)))
        return resolved

    def resolved_constant(self, instance):
        from solid_node.parameters import evaluate

        return evaluate(self.constant,
                        instance.__dict__.get('_parameters', {}))


def _shared_domain(terms):
    """The domain and unit a formula's terms share, or the refusal
    naming the two that disagree."""
    domain = unit = None
    domain_term = unit_term = None
    for term in terms:
        found = term.domain
        if found is not None:
            if domain is not None and found != domain:
                raise TypeError(
                    f'{domain_term.described()} carries a {domain} value and '
                    f'{term.described()} a {found} one, so the two cannot be '
                    f'terms of one derived coordinate: a formula over '
                    f'coordinates keeps one domain. Write the relation with '
                    f'law=, whose ratio converts.')
            domain, domain_term = found, term
        stated = term.unit
        if stated is not None:
            if unit is not None and stated != unit:
                raise TypeError(
                    f"{unit_term.described()} states the unit '{unit}' and "
                    f"{term.described()} states '{stated}', so the two "
                    f"cannot be terms of one derived coordinate. Convert "
                    f"with a relation, whose ratio is the conversion.")
            unit, unit_term = stated, term
    return domain, unit


##############################################
# The relation

class Relation:
    """`a.drives(b)`: two ends and a law, recorded on the class.

    A NON-data descriptor, like `ChildDeclaration`: read off the class a
    named relation hands back the declaration, read off an instance it
    hands back that instance's record -- the two resolved coordinates,
    the law, and which way it was solved on the last run.
    """

    _names_in_body = True
    _name = None
    owner = None

    def __init__(self, driver, driven, ratio, offset, law):
        self.driver = driver
        self.driven = driven
        self.ratio = ratio
        self.offset = offset
        self.callable_law = law
        self.law = law if law is not None else Affine(
            1 if ratio is None else ratio,
            0 if offset is None else offset)

    @property
    def name(self):
        return self._name

    def __set_name__(self, owner, name):
        self._name = name
        self.owner = owner

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self.record_of(instance)

    def record_of(self, instance):
        matches = [record for record in instance.__dict__.get('_relations', ())
                  if record.relation is self]
        if _is_broadcast(self.driven):
            # A broadcast's shape, not its count: a tuple even when the
            # repeat realized zero copies (design.md open question 2).
            return tuple(matches)
        if matches:
            return matches[0]
        raise AttributeError(
            f'{self} is not resolved on this {type(instance).__name__}')

    def described(self):
        written = f'{self.driver.described()} drives {self.driven.described()}'
        return f"'{self.name}' ({written})" if self.name else written

    def check_declared_on(self, owner):
        self.driver.check_declared_on(owner, self)
        self.driven.check_declared_on(owner, self)

    def __repr__(self):
        return f'<relation {self.described()}>'

    def resolve(self, instance):
        """This instance's record of the relation -- ONE for an
        ordinary relation, one PER REALIZED COPY for a broadcast (see
        `couplings` spec, "Each end of a relation resolves to a
        coordinate, or to one per copy of a repeated child").

        An end naming several coordinates resolves to a TUPLE of
        `ResolvedEnd`s rather than one: the law's argument for that end
        is then the tuple of their owners (`_law_argument`), and the
        record's `driver_ends`/`driven_ends` carry all of them
        (design.md sections 3 and 5)."""
        from solid_node.parameters import evaluate

        driver_ends = _resolve_ends(self.driver, instance)
        if _is_broadcast(self.driven):
            per_copy = _resolve_ends_per_copy(self.driven, instance)
            if self.callable_law is None:
                values = instance.__dict__.get('_parameters', {})
                law = Affine(
                    1 if self.ratio is None else evaluate(self.ratio, values),
                    0 if self.offset is None
                    else evaluate(self.offset, values))
                # The SAME law object for every copy: a ratio names a
                # value of the DECLARING class and has no way to see a
                # copy (design.md decision 5).
                return [RelationRecord(self, driver_ends, driven_ends, law,
                                       copy=copy_node)
                        for copy_node, driven_ends in per_copy]
            driver_owner = _law_argument(driver_ends)
            records = []
            for copy_node, driven_ends in per_copy:
                # Called once per COPY, at realization, with the copy's
                # own owners: the owner of a driven coordinate under a
                # broadcast is the copy (couplings spec, "The law of a
                # relation is an affine pair, or project code passed
                # in").
                returned = self.callable_law(driver_owner,
                                             _law_argument(driven_ends))
                law = as_law(returned, self.described())
                records.append(RelationRecord(self, driver_ends, driven_ends,
                                              law, copy=copy_node))
            return records
        driven_ends = _resolve_ends(self.driven, instance)
        if self.callable_law is not None:
            returned = self.callable_law(_law_argument(driver_ends),
                                         _law_argument(driven_ends))
            law = as_law(returned, self.described())
        else:
            values = instance.__dict__.get('_parameters', {})
            law = Affine(
                1 if self.ratio is None else evaluate(self.ratio, values),
                0 if self.offset is None else evaluate(self.offset, values))
        return [RelationRecord(self, driver_ends, driven_ends, law)]


class RelationRecord:
    """One instance's resolved relation: what it relates, the law it got
    at realization, and which way the last run solved it.

    `driver_ends` and `driven_ends` are TUPLES of `ResolvedEnd`, of
    length n and m -- one each for an ordinary one-to-one relation,
    several when either end names a group. `driver_end`/`driven_end`
    stay as properties for that n = m = 1 case, which every existing
    reader still uses.

    `copy` is the node the REPEATED SEGMENT itself realized, for a
    broadcast -- None for an ordinary relation's one record."""

    def __init__(self, relation, driver_ends, driven_ends, law, copy=None):
        self.relation = relation
        self.driver_ends = tuple(driver_ends)
        self.driven_ends = tuple(driven_ends)
        self.law = law
        self.direction = None
        self.copy = copy

    @property
    def name(self):
        return self.relation.name

    @property
    def driver_end(self):
        return self.driver_ends[0]

    @property
    def driven_end(self):
        return self.driven_ends[0]

    @property
    def driver(self):
        return self.driver_end.slot

    @property
    def driven(self):
        return self.driven_end.slot

    @property
    def driver_owner(self):
        return self.driver_end.node

    @property
    def driven_owner(self):
        return self.driven_end.node

    def described(self):
        base = self.relation.described()
        if self.copy is None:
            return base
        return f'{base}, copy {getattr(self.copy, "name", self.copy)}'

    def __repr__(self):
        return (f'<relation {self.described()} '
                f'solved {self.direction or "not yet"}>')


def _is_descendant_or_self(node, ancestor):
    """Whether `node` IS `ancestor` or hangs below it, through the
    `_parent` links a walker's own linking sets (`_link_children`) --
    the same climb `qualified.instance_path` makes, stopped at the
    first match instead of collecting names."""
    current = node
    while current is not None:
        if current is ancestor:
            return True
        current = getattr(current, '_parent', None)
    return False


class ResolvedEnd:
    """One end of one instance's relation: the realized node that owns
    the coordinate, and the way to read and bind it."""

    def __init__(self, node, declared, ref):
        self.node = node
        self.declared = declared
        self.ref = ref
        self.is_driver = _coordinate_of(declared) is None
        self.slot = (None if self.is_driver
                     else _coordinate_of(declared).__get__(node))

    @property
    def name(self):
        return _declaration_name(self.declared)

    def described(self):
        return f'{where(self.node)}.{self.name}'

    def bound(self):
        if self.is_driver:
            return True
        if self.slot._value is None:
            return False
        if self.slot._enum_marker is _current_enumeration():
            # Bound during THIS pass -- by whichever assembly, including
            # one still ahead of whatever is currently attempting
            # (design.md section 6's "some OTHER assembly has ALREADY
            # bound it" case): unambiguously this enumeration's answer.
            return True
        # A non-None value that is not this enumeration's: either a
        # leftover from an EARLIER one, or one bound outside any
        # enumeration at all (a hand assignment before the first
        # render(), between two `render()` calls, in a bare
        # construction -- `_bound_by` is None then, never having been
        # set inside a phase). Whether a leftover counts as "bound" now
        # depends on whether the assembly that put it there is due to
        # attempt again before this pass concludes: if some assembly's
        # OWN attempt is currently running (`_current_phase()`) and the
        # slot's last binder is that SAME assembly or one of ITS OWN
        # descendants, tree order guarantees that assembly (or one
        # below it) has not run its phase yet THIS enumeration but will
        # -- the walker always finishes an assembly's whole subtree
        # before the pass closes -- so the value is not yet this
        # enumeration's and this end defers; the descendant's fresh
        # rebind, later in the SAME pass, is what `run_deferred` then
        # reads. Otherwise -- nothing running right now, as when the
        # pass's own fixpoint reads a leftover once every phase in the
        # enumeration has already run; the slot's binder unset entirely;
        # or the binder's assembly outside whatever is currently
        # attempting, such as an ANCESTOR's relation a partially
        # re-rendered subtree can no longer reach because that ancestor
        # sits outside the subtree THIS pass walks
        # (`_lifecycle_render`'s own re-attempt of a node whose owning
        # enumeration already closed) -- nothing here is about to
        # reclaim it, so it is this pass's final answer for it, exactly
        # as one bound outside any enumeration always reads (design.md
        # section 6): trust it.
        phase = _current_phase()
        binder_assembly = self.slot._bound_by
        if (phase is not None and binder_assembly is not None
                and _is_descendant_or_self(binder_assembly, phase.assembly)):
            return False
        return True

    def value(self):
        if self.is_driver:
            # An unbound driver fails loudly here exactly as it does in
            # a simulate() that reads one: a value invented for it would
            # be a pose nobody stated.
            return getattr(self.node, _declaration_name(self.declared))
        return self.slot._value

    def bind(self, value, binder):
        """Bind through the ONE binding path an author's binding takes,
        so the sink's scale, a joint's range and a joint's placement
        behave exactly as they do for a hand binding."""
        from solid_node.motion.joints import Joint

        if self.is_driver:
            raise CouplingError(
                f'{self.described()} is a driver and cannot be bound by a '
                f'relation; its value belongs to the bound snapshot.')
        with binding_as(binder):
            if isinstance(self.declared, (Joint, Port)):
                # Through the coordinate's own NAME, whatever kind of
                # name it is: a plain one is an attribute of the node,
                # and a dotted one reaches the joint that owns it.
                set_coordinate(self.node,
                               _declaration_name(self.declared), value)
            else:
                bind(self.slot, value)
        return self.slot


def where(node):
    """How a node is named in a refusal: its path under the root of the
    tree it hangs in, or its name and class when nothing linked it."""
    from solid_node.node.assembly import top_of
    from solid_node.node.qualified import DriverIdError, instance_path

    root = top_of(node)
    if root is not node:
        try:
            path = instance_path(node, root)
        except DriverIdError:
            path = ()
        if path:
            return '.'.join(path)
    return f'{getattr(node, "name", node)} ({type(node).__name__})'


##############################################
# Stating a relation

def relate(driver, driven, ratio=None, offset=None, law=None):
    """`driver.drives(driven, ...)`: the one verb, recorded on the class
    body that is executing."""
    from solid_node.node.declarative import record_relation

    if law is not None and (ratio is not None or offset is not None):
        raise TypeError(
            'a relation carries one law: ratio= and offset= are the '
            'shorthand for Affine, and law= is a callable returning one, so '
            'stating both is two ways to say one thing. Put the ratio inside '
            'the law, or drop law=.')
    driver_ref = coordinate_ref(driver, 'driver')
    driven_ref = coordinate_ref(driven, 'driven')
    driver_ref.check('driver')
    driven_ref.check('driven')
    several = len(_end_refs(driver_ref)) > 1 or len(_end_refs(driven_ref)) > 1
    if several:
        if law is None:
            raise TypeError(
                f'{driver_ref.described()} drives {driven_ref.described()}: '
                f'a relation naming several ends carries a law=. An affine '
                f'law relates one value to one value, and ratio=/offset= '
                f'are its shorthand, so neither states several ends.')
        _refuse_shared_coordinate(driver_ref, driven_ref)
    relation = Relation(driver_ref, driven_ref, ratio, offset, law)
    record_relation(relation)
    return relation


def coordinate_ref(value, role='end'):
    """`value` as a coordinate reference, whatever kind of declaration
    the class body wrote."""
    from solid_node.node.declarative import (ChildDeclaration,
                                             RepeatDeclaration)
    from solid_node.node.qualified import DriverDeclaration

    if isinstance(value, CoordinateRef):
        return value
    if isinstance(value, (Coordinates, tuple)):
        return _end_group(value, role)
    if _coordinate_of(value) is not None:
        return OwnRef(value)
    if _coordinates_of(value) is not None:
        # The joint itself, named in the class body that declares it:
        # `pose.drives(...)`, or `tilt.drives(pose)`.
        raise _refuse_several_coordinates(value, value.name or repr(value))
    if isinstance(value, ChildDeclaration):
        return PathRef(value, (), value)
    if isinstance(value, RepeatDeclaration):
        # The repeat's own one joint, bare: `earth.drives(beads)` or
        # `beads.drives(earth)`. `check(role)` refuses the second as a
        # SOURCE; the first is an ordinary broadcast.
        return BroadcastRef(value, (), value, value)
    if isinstance(value, DriverDeclaration):
        return DriverRef(value)
    if _is_declaration_list(value):
        name = _named_in_body(value) or repr(value)
        raise TypeError(
            f"'{name}' holds {len(value)} children, each with its own "
            f"arguments -- named '{name}-0', '{name}-1', and so on, one by "
            f"one -- so it cannot be the {role} end of a relation naming "
            f"all of them at once. Name one child by its own attribute.")
    raise TypeError(
        f'{value!r} is not a coordinate, so it cannot be the {role} end of a '
        f'relation. An end is a port, a joint, a child declaration, a path '
        f'through one, a derived coordinate or a Driver.')


##############################################
# Enumeration

_relations_cache = {}
_derived_cache = {}


def declared_relations(node_class):
    """Every relation declared on `node_class`, base-first through the
    inheritance chain.

    A relation written as a BARE STATEMENT has no name, and a subclass
    ADDS such a relation to its bases' rather than overriding them --
    a statement is not a name. A relation ASSIGNED to a name, when a
    subclass assigns a relation to a name one of its bases already used,
    REPLACES the base's: the base's own relation is dropped from the
    subclass's enumeration and the replacing one keeps the position the
    base's held (the rule a redeclared joint already obeys,
    `declared_joints`/ADR-093), so the pass order does not shift under
    inheritance. Walked base-first (`reversed(node_class.__mro__)`), so a
    base's relations arrive before a subclass's, and a subclass's own
    replace the matching names as they are found.
    """
    cached = _relations_cache.get(node_class)
    if cached is None:
        found = []
        positions = {}
        for klass in reversed(getattr(node_class, '__mro__', ())):
            for relation in vars(klass).get('_declared_relations', ()):
                if any(relation is seen for seen in found):
                    continue
                name = relation.name
                if name is not None and name in positions:
                    found[positions[name]] = relation
                else:
                    if name is not None:
                        positions[name] = len(found)
                    found.append(relation)
        cached = _relations_cache[node_class] = tuple(found)
    return cached


def declared_derived(node_class):
    """Every derived coordinate declared on `node_class`, by name."""
    cached = _derived_cache.get(node_class)
    if cached is None:
        found = {}
        for klass in reversed(getattr(node_class, '__mro__', ())):
            for name, value in vars(klass).items():
                if isinstance(value, DerivedCoordinate):
                    found[name] = value
        cached = _derived_cache[node_class] = found
    return cached


def resolve_declared_relations(node):
    """Resolve every relation of `node`'s class against this instance,
    and call every `law=` callable once.

    At the END of the instance's construction, after its children are
    realized, because an end may be a child or a descendant of one.
    """
    relations = declared_relations(type(node))
    if not relations:
        return
    records = []
    for relation in relations:
        # A broadcast resolves to n records at the position of its
        # declaration, in copy order; an ordinary relation to one. The
        # flattened list is what keeps the fixpoint's own iteration --
        # and its "declaration order, copy order within it" -- a single
        # flat pass (couplings spec, "Relations are solved from the
        # bound side").
        records.extend(relation.resolve(node))
    node.__dict__['_relations'] = records


##############################################
# The solver

class Wiring:
    """A wiring, as the forward-only identity relation it already is."""

    def __init__(self, parent, child, keyword, source):
        self.parent = parent
        self.child = child
        self.keyword = keyword
        self.source = source
        self.slot = source.__get__(parent)
        self.target = declared_ports(type(child))[keyword].__get__(child)
        self.applied = False

    def described(self):
        return (f'the wiring {type(self.parent).__name__}.{self.source.name} '
                f'-> {self.keyword} of {self.child.name}')

    def apply(self):
        with binding_as(self):
            with wiring_binding():
                set_coordinate(self.child, self.keyword, self.slot)
        self.applied = True

    def unbound_source(self):
        return ValueError(
            f"cannot wire {type(self.parent).__name__}."
            f"{self.source.name} into '{self.keyword}' of "
            f"{self.child.name}: nothing has bound it. A wiring "
            f"delivers the parent's value to the child, so the "
            f"parent's own coordinate has to be bound first -- "
            f"in {type(self.parent).__name__}.simulate(), before "
            f"it returns.")


def _wirings(assembly):
    from solid_node.node.declarative import declared_child_nodes

    found = []
    for child in declared_child_nodes(assembly):
        wiring = child.__dict__.get('_wired_from')
        if not wiring:
            continue
        for keyword, source in wiring.items():
            found.append(Wiring(assembly, child, keyword, source))
    return found


def _solved_formulas(assembly, records):
    """The derived coordinates this instance solves: every one the
    class declares, and every anonymous one a relation names as an end."""
    found = list(declared_derived(type(assembly)).values())
    for record in records:
        members = _end_refs(record.relation.driver) + _end_refs(
            record.relation.driven)
        for ref in members:
            if (isinstance(ref, DerivedCoordinate)
                    and not any(ref is seen for seen in found)):
                found.append(ref)
    return found


def clear_solved(assembly):
    """Drop what THIS assembly bound during its PREVIOUS simulate phase,
    at the start of this one -- whoever bound it: a relation, a wiring, a
    derived coordinate, or the author's own `simulate()`.

    A value slot keeps what was put into it, and nothing else clears it:
    without this the second run would find every coordinate still
    holding the first run's value, the fixpoint would find no relation
    with exactly one bound end, and the train would stay frozen at the
    first instant. The author's binding is cleared with the rest now
    (`whole-tree-fixpoint`): the value and the swept motion are two
    halves of one binding, and dropping only one of them is what left a
    rest-default joint standing at a stale number with no operation left
    to show for it.

    A slot this assembly bound LAST enumeration and some OTHER assembly
    has ALREADY bound again in the current one -- an ancestor's relation
    claiming a coordinate this same node's own rest-default guard
    otherwise fills, on a run where the ancestor reaches it first -- is
    left alone: it is not stale, it is fresh, and clearing it here would
    erase a value the current pass already produced correctly, before
    this assembly's own phase (later in the same cascade) even runs.
    `_enum_marker` (set by every `bind`) is what tells the two apart.
    """
    current_enumeration = _current_enumeration()
    for slot in assembly.__dict__.pop('_solver_bound', ()):
        if slot._enum_marker is current_enumeration:
            continue
        slot._value = None
        slot.binder = None


class _Deferred:
    """One assembly's LEFTOVER relations, derived coordinates and
    wirings after its own attempt -- what its own instance's phase could
    not resolve, carried into the enumeration's fixpoint.

    `claimed` and `bound` are the SAME objects the per-instance attempt
    used, so a coordinate the enumeration's fixpoint goes on to claim is
    still checked against every claim this assembly's own attempt already
    made, and a slot the fixpoint binds still lands in the list this
    assembly's OWN next `clear_solved` reads.
    """

    __slots__ = ('assembly', 'records', 'derived', 'wirings', 'claimed',
                'bound')

    def __init__(self, assembly, records, derived, wirings, claimed, bound):
        self.assembly = assembly
        self.records = records
        self.derived = derived
        self.wirings = wirings
        self.claimed = claimed
        self.bound = bound


def _formula_unresolved(assembly, formula):
    """Whether a derived coordinate is the shape `_refuse` complains
    about: BOUND while more than one of its terms is not. A formula
    nothing has bound is inert, not a candidate to defer -- exactly as
    `_refuse` never raises for one today."""
    slot = formula.slot_of(assembly)
    if slot._value is None:
        return False
    unbound = [end for end, _coefficient
              in formula.resolved_terms(assembly) if not end.bound()]
    return len(unbound) > 1


def solve_relations(assembly, enumeration):
    """ATTEMPT this instance's relations and wirings, at the end of its
    simulate phase: exactly the inventory-then-propagate fixpoint this
    always was, over this instance's own records alone.

    What the attempt cannot reach is DEFERRED to `enumeration` rather
    than refused -- a `_Deferred` bundle of whatever is left, carrying
    the SAME `claimed`/`bound` this attempt used, so the enumeration's
    own fixpoint (`run_deferred`) can go on claiming and binding into
    them. A DOUBLY BOUND coordinate is never deferred: `_step_relation`,
    `_step_derived` and `_step_wiring` still raise it here, immediately,
    exactly as they always have.
    """
    records = assembly.__dict__.get('_relations', ())
    derived = _solved_formulas(assembly, records)
    wirings = _wirings(assembly)
    if not records and not derived and not wirings:
        return
    for record in records:
        record.direction = None
    # The phase's OWN bound list: the author's simulate() has already
    # been recording into it (`ports.bind` -> `phase.note_bound`), and
    # `assembly.py` records this SAME list as `_solver_bound` once this
    # phase finishes, whether or not this attempt finds anything to
    # solve -- so starting from it here means clear_solved's next run
    # drops the author's rest-default binding together with whatever
    # this attempt and the enumeration's own fixpoint go on to add.
    bound = _current_phase().bound
    claimed = {id(wiring.target): wiring for wiring in wirings}

    changed = True
    while changed:
        changed = False
        for record in records:
            changed = _step_relation(record, claimed, bound) or changed
        for formula in derived:
            changed = _step_derived(assembly, formula, claimed,
                                    bound) or changed
        for wiring in wirings:
            changed = _step_wiring(wiring, bound) or changed

    leftover_records = [record for record in records
                        if record.direction is None]
    leftover_derived = [formula for formula in derived
                        if _formula_unresolved(assembly, formula)]
    leftover_wirings = [wiring for wiring in wirings if not wiring.applied]
    if leftover_records or leftover_derived or leftover_wirings:
        enumeration.deferred.append(_Deferred(
            assembly, leftover_records, leftover_derived, leftover_wirings,
            claimed, bound))


def run_deferred(enumeration):
    """The enumeration's own fixpoint: propagate over every assembly's
    leftover relations, derived coordinates and wirings, in TREE
    ORDER -- the order `enumeration.deferred` was appended in, which is
    the order the assemblies' phases ran, parents before children -- and
    within one assembly the declaration order its own attempt already
    preserved. Repeats until nothing changes any more, then refuses
    whatever is left, by the SAME `_refuse` a single instance's own
    attempt always called.

    Every step function is the one the per-instance attempt uses,
    unchanged: `_step_relation`/`_step_derived`/`_step_wiring` are
    idempotent once a record has solved (their own "already bound"
    checks return False), so scanning the WHOLE leftover list again on
    every round is simply the fixpoint, not wasted work repeated.
    """
    changed = True
    while changed:
        changed = False
        for unit in enumeration.deferred:
            for record in unit.records:
                changed = _step_relation(record, unit.claimed,
                                         unit.bound) or changed
            for formula in unit.derived:
                changed = _step_derived(unit.assembly, formula,
                                        unit.claimed, unit.bound) or changed
            for wiring in unit.wirings:
                changed = _step_wiring(wiring, unit.bound) or changed
    for unit in enumeration.deferred:
        _refuse(unit.assembly, unit.records, unit.derived, unit.wirings)


def refuse_reads(enumeration):
    """The read-refusal rule, judged at the end of the enumeration: a
    recorded read of a coordinate slot that was, by now, bound by a
    relation, a derived coordinate or a wiring is refused by name. A read
    the AUTHOR went on to bind (the rest-default guard) or that stayed
    unbound (the unreached coordinate, refused by its own name elsewhere)
    is not this rule's business.
    """
    for slot, reading_node, reader, filename, lineno in enumeration.reads:
        if slot._value is None:
            continue
        binder = getattr(slot, 'binder', None)
        if binder is None:
            continue
        coordinate_path = f'{where(slot.node)}.{slot.name}'
        raise PrematureRead(
            f"{coordinate_path} was read by {reader.__name__}'s own "
            f'simulate() ({where(reading_node)}, {filename}:{lineno}) '
            f'before {_describe_binder(binder)} bound it: simulate() runs '
            f'first, the relations of the class that states the binder are '
            f"solved after it returns, and a descendant's after that. The "
            f'whole-tree fixpoint makes the SENTENCE statable, not the '
            f'value early.')


def _binder_of(slot):
    return getattr(slot, 'binder', None)


def _describe_binder(binder):
    if binder is None:
        return "the author's simulate()"
    if isinstance(binder, RelationRecord):
        return f'the relation {binder.described()}'
    if isinstance(binder, Wiring):
        return binder.described()
    if isinstance(binder, DerivedCoordinate):
        return f'the derived coordinate {binder.described()} ({binder.written})'
    return repr(binder)


def _refuse_double(target, binder, coordinate):
    raise DoublyBound(
        f'{coordinate} would be bound by {_describe_binder(binder)} and by '
        f'{_describe_binder(_binder_of(target))}. A coordinate has exactly '
        f'one binder in one enumeration of the tree, and the framework does '
        f'not compare two values to decide whether two statements agree: '
        f'they are ordinarily symbolic expressions. Drop one of them.')


def _claim(end, binder, claimed):
    """Refuse before binding when something else already owns the
    target: a wiring that declared it, or a binder that reached it."""
    wiring = claimed.get(id(end.slot))
    if wiring is not None and wiring is not binder:
        raise DoublyBound(
            f'{end.described()} would be bound by '
            f'{_describe_binder(binder)} and by {wiring.described()}. A '
            f'wired coordinate has one binder, and the framework does not '
            f'compare two values to decide whether two statements agree. '
            f'Drop the wiring, or the relation.')
    if end.bound():
        _refuse_double(end.slot, binder, end.described())


def _step_relation(record, claimed, bound):
    driver_ends = record.driver_ends
    driven_ends = record.driven_ends
    several = len(driver_ends) > 1 or len(driven_ends) > 1

    if not several:
        # The n = m = 1 case, unchanged: either direction, whichever end
        # is bound.
        driver_end = driver_ends[0]
        driven_end = driven_ends[0]
        driver_bound = driver_end.bound()
        driven_bound = driven_end.bound()
        if driver_bound and driven_bound:
            if record.direction is not None:
                return False
            _refuse_double(
                driven_end.slot if driven_end.slot is not None
                else driver_end.slot,
                record, driven_end.described())
        if driver_bound:
            _claim(driven_end, record, claimed)
            value = record.law.forward(driver_end.value())
            bound.append(driven_end.bind(value, record))
            record.direction = 'forward'
            return True
        if driven_bound:
            if isinstance(record.relation.driven, BroadcastRef):
                # A broadcast is read forward only, whatever its law
                # offers: the n copies would have to agree on one source
                # value, and the framework does not compare values to
                # decide that (couplings spec, "Three refusals").
                # Deferred here exactly as a non-invertible law is --
                # the author's own binding may still reach the driver
                # end -- and `_refuse` raises if it never does.
                return False
            if not invertible(record.law):
                # Deferred: another relation may still bind the driver
                # end, and a law that is never needed backwards is never
                # refused.
                return False
            _claim(driver_end, record, claimed)
            value = record.law.inverse(driven_end.value())
            bound.append(driver_end.bind(value, record))
            record.direction = 'backward'
            return True
        return False

    # A relation naming SEVERAL coordinates at either end: forward only,
    # applied when every source is bound, all its driven ends claimed
    # and bound together (couplings spec, "A relation may name several
    # coordinates at each end").
    if record.direction is not None:
        return False
    if not all(end.bound() for end in driver_ends):
        return False
    for end in driven_ends:
        _claim(end, record, claimed)
    values = record.law.forward(*[end.value() for end in driver_ends])
    if len(driven_ends) == 1:
        values = (values,)
    else:
        values = _checked_return(record, values, driven_ends)
    for end, value in zip(driven_ends, values):
        bound.append(end.bind(value, record))
    record.direction = 'forward'
    return True


def _checked_return(record, returned, driven_ends):
    """`returned` as the SEQUENCE of exactly `len(driven_ends)` values a
    multi-target law's `forward` owes -- refused by name, naming the
    relation, the law, the driven ends as written and what came back,
    rather than bound: a value slot accepts whatever is put into it, and
    a wrong-shaped return would be a pose nobody stated (design.md
    section 3)."""
    length = None
    if not isinstance(returned, str):
        try:
            length = len(returned)
        except TypeError:
            length = None
    if length != len(driven_ends):
        names = ', '.join(end.described() for end in driven_ends)
        raise CouplingError(
            f'{record.described()}: the law {record.law!r} returned '
            f'{returned!r} for {len(driven_ends)} driven ends ({names}), '
            f'which is not a sequence of exactly {len(driven_ends)} values. '
            f'A value slot accepts whatever is put into it, and a '
            f'wrong-shaped return would be a pose nobody stated.')
    return returned


def _step_derived(assembly, formula, claimed, bound):
    slot = formula.slot_of(assembly)
    terms = formula.resolved_terms(assembly)
    unbound = [(end, coefficient) for end, coefficient in terms
               if not end.bound()]
    if slot._value is None:
        if unbound:
            return False
        value = formula.resolved_constant(assembly)
        for end, coefficient in terms:
            term = end.value()
            term = term if _is_one(coefficient) else coefficient * term
            value = term if _is_zero(value) else value + term
        with binding_as(formula):
            bind(slot, value)
        bound.append(slot)
        return True
    if len(unbound) != 1:
        return False
    end, coefficient = unbound[0]
    _claim(end, formula, claimed)
    value = slot._value
    constant = formula.resolved_constant(assembly)
    if not _is_zero(constant):
        value = value - constant
    for other, other_coefficient in terms:
        if other is end:
            continue
        term = other.value()
        term = (term if _is_one(other_coefficient)
                else other_coefficient * term)
        value = value - term
    if not _is_one(coefficient):
        value = value / coefficient
    bound.append(end.bind(value, formula))
    return True


def _step_wiring(wiring, bound):
    if wiring.applied or wiring.slot._value is None:
        return False
    if wiring.target._value is not None:
        _refuse_double(wiring.target, wiring,
                       f'{where(wiring.child)}.{wiring.keyword}')
    wiring.apply()
    bound.append(wiring.target)
    return True


def _refuse(assembly, records, derived, wirings):
    for record in records:
        if record.direction is not None:
            continue
        driver_ends = record.driver_ends
        driven_ends = record.driven_ends
        if len(driver_ends) > 1 or len(driven_ends) > 1:
            unbound_sources = [end for end in driver_ends if not end.bound()]
            bound_driven = [end for end in driven_ends if end.bound()]
            if bound_driven:
                bound_names = ', '.join(end.described() for end in bound_driven)
                source_names = ', '.join(end.described()
                                         for end in unbound_sources)
                raise NotInvertible(
                    f'{record.described()}: {bound_names} '
                    f'{"is" if len(bound_driven) == 1 else "are"} bound, so '
                    f'the relation would have to be read backwards -- but a '
                    f'relation naming several ends is read forward only, '
                    f'whatever its law offers: recovering the sources from '
                    f'the driven values would mean comparing or solving '
                    f'values, which the framework does not do. '
                    f'{source_names} '
                    f'{"is" if len(unbound_sources) == 1 else "are"} still '
                    f'unbound; bind '
                    f'{"it" if len(unbound_sources) == 1 else "them"} '
                    f'instead.')
            source_names = ', '.join(end.described() for end in unbound_sources)
            raise UnreachedCoordinate(
                f'{record.described()}: waiting for {source_names}. '
                f'{"It is" if len(unbound_sources) == 1 else "They are"} '
                f'unbound when nothing changes any more, and no driven end '
                f'is bound either, so the relation has no side to be read '
                f'from. Bind '
                f'{"it" if len(unbound_sources) == 1 else "them"} in '
                f'simulate(), or state a relation that reaches '
                f'{"it" if len(unbound_sources) == 1 else "them"}.')
        driver_bound = record.driver_end.bound()
        driven_bound = record.driven_end.bound()
        if driven_bound and not driver_bound:
            if isinstance(record.relation.driven, BroadcastRef):
                raise NotInvertible(
                    f'{record.described()}: {record.driven_end.described()} '
                    f'is bound, so the relation would have to be read '
                    f'backwards -- but a broadcast is read forward only, '
                    f'whatever its law offers: the copies hold one value '
                    f'each, and deriving one source value from them would '
                    f'mean comparing values, which the framework does not '
                    f'do. Bind {record.driver_end.described()} instead.')
            raise NotInvertible(
                f'{record.described()}: {record.driven_end.described()} is '
                f'the bound end, so the relation has to be read backwards, '
                f'and its law {record.law!r} offers no inverse. Give the law '
                f'an inverse(y), or bind '
                f'{record.driver_end.described()} instead.')
        if not driver_bound and not driven_bound:
            raise UnreachedCoordinate(
                f'{record.described()}: nothing bound either end. '
                f'{record.driver_end.described()} and '
                f'{record.driven_end.described()} are both unbound when '
                f'nothing changes any more, so the relation has no side to '
                f'be read from. Bind one of them in simulate(), or state a '
                f'relation that reaches one.')
    for formula in derived:
        slot = formula.slot_of(assembly)
        if slot._value is None:
            continue
        unbound = [end for end, _coefficient
                   in formula.resolved_terms(assembly) if not end.bound()]
        if len(unbound) > 1:
            names = ', '.join(end.described() for end in unbound)
            raise UnreachedCoordinate(
                f"the derived coordinate "
                f"'{formula._name or formula.written}' "
                f"({formula.written}) is bound while {len(unbound)} of its "
                f"terms are not: {names}. One equation solves one unknown; "
                f"bind the others, or state relations that reach them.")
    for wiring in wirings:
        if not wiring.applied:
            raise wiring.unbound_source()
