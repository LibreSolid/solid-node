# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A pair that places a body.

A revolute joint exists in every project in the catalogue and, until
this module, in no line of the framework: it was an emergent property of
the author having written `self.rotate(self.angle, [0, 0, 1])` and, when
the axis does not run through the moving part's own origin, of the frame
arithmetic that carries a pivot into that part's coordinates as well.
`Revolute` and `Prismatic` are the two one-coordinate lower pairs
stated once, next to the body they move.

A joint is declared as a class attribute of the node it moves and says
WHERE that node may move::

    class Forearm(AssemblyNode):
        elbow = Revolute(axis=(0, 0, 1), at=(0, 160, 68),
                         range=(-135, 135), unit='deg')

`axis` and `at` are read in the PARENT's frame -- the frame the parent's
`render()` places this node in, which is where MuJoCo's `hinge` and
Modelica's `Joints.Revolute` state them too. The framework carries them
into the node's own frame by inverting the node's rest placement, which
is exactly the arithmetic a project writes by hand today, and then
places the body about the carried line.

A joint OWNS one coordinate, and that coordinate is a port: read on an
instance a joint IS its bound port slot, and assigning to it binds
through the one binding path `connect()` uses. It is not a `Port`
subclass, though: a port carries a value between nodes, while a joint
additionally places a body and carries an axis, an anchor and a range,
and subclassing would put `axis` on every port and let a wire into a
joint be typed as an ordinary port-to-port connection. Composition
keeps the two questions apart; `declared_ports` reports the coordinate
under the joint's name so every consumer of a node's connection points
sees it without knowing what a joint is, and `declared_joints` here is
the sibling for the code that needs the axis and the anchor.

Module scope imports `solid_node.motion.ports` and nothing else: a joint
owns a port, so that cost is unavoidable, and everything from the node
package -- the operations, the placement seam, the tree -- is reached
inside the method that needs it, exactly as `Time` reaches
`AssemblyNode`. Importing this module pulls no CAD backend, no exact
stack and no `trimesh`; the `matrix()` calls that pull `trimesh` happen
at binding time, inside a live render where geometry is loaded anyway.
"""

import math

from solid_node.motion.ports import (BoundPort, Port, RotationalPort,
                                     TranslationalPort, bind)


__all__ = ['Joint', 'JointRangeError', 'Prismatic', 'Revolute',
           'declared_joints']


# How close to an exact 0, 1 or -1 a carried component has to be before
# it IS that value. Inverting a rest placement leaves floating-point
# residue -- an axis comes back as (0, 1, 6e-17) -- and whatever comes
# back is what the published document carries, so the residue is snapped
# away before anything reads it.
_SNAP = 1e-9

_MISSING = object()


class JointRangeError(ValueError):
    """A joint was bound to a number outside its declared range."""


def _snapped(value):
    """`value`, or the exact 0, 1 or -1 it is within `_SNAP` of."""
    for exact in (0, 1, -1):
        if abs(value - exact) <= _SNAP:
            return exact
    return value


def _where(node):
    """How a node is named in a joint's error: its path under the root
    of the tree it hangs in, or its name and class when nothing has
    linked it yet.

    A node bound before any walker linked it has no path -- the names
    a path is made of are the ones a parent derives from the attribute
    holding the child -- and inventing one would name the wrong node.
    """
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
    return f'{node.name} ({type(node).__name__})'


class Joint:
    """The shared base of the one-coordinate lower pairs.

    A data descriptor, so an assignment binds the coordinate instead of
    quietly replacing the declaration with a raw number. Stateless class
    metadata like a port declaration: the bound value lives in the
    instance's own port slot, and the resolved axis, anchor and range
    live in the instance's own `_joint_arguments`.
    """

    # The port kind the subclass's coordinate is, and the unit it
    # carries when the declaration names none.
    coordinate_kind = None
    default_unit = None

    def __init__(self, axis, at=(0, 0, 0), range=None, unit=None):
        self.axis = axis
        self.at = at
        self.range = range
        self.unit = self.default_unit if unit is None else unit
        self.name = None
        self.owner = None
        # The one coordinate this joint owns. Created here rather than
        # per instance for the same reason a port declaration is class
        # metadata: it must be readable off the class, and the VALUE it
        # names lives in the instance's slot, not here.
        self.coordinate = self.coordinate_kind(unit=self.unit)

    ##############################################
    # Declaration

    def __set_name__(self, owner, name):
        for klass in owner.__mro__[1:]:
            existing = vars(klass).get(name, _MISSING)
            if existing is _MISSING or isinstance(existing, Joint):
                # Absent, or an inherited joint this one redeclares --
                # base-first enumeration lets a subclass redeclare, and
                # that stays legal.
                continue
            raise TypeError(
                f"joint '{name}' on {owner.__name__} would shadow "
                f"{klass.__name__}.{name}, which a read of the joint would "
                f"then hide for good. A joint is read as an attribute of "
                f"its node, so its name has to be free on that node: "
                f"rename the joint.")
        self.name = name
        self.owner = owner
        # The coordinate answers to the joint's own name: it is what
        # `declared_ports` reports, and what an error about the binding
        # has to be able to say.
        self.coordinate.name = name
        self.coordinate.owner = owner

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self.coordinate.__get__(instance)

    def __set__(self, instance, value):
        slot = self.coordinate.__get__(instance)
        self._refuse_out_of_range(instance, value)
        bind(slot, value)
        self.place(instance, slot.value)

    def __repr__(self):
        return (f'<{type(self).__name__} {self.name} '
                f'axis={self.axis!r} at={self.at!r}>')

    ##############################################
    # Arguments

    def resolve(self, node, values):
        """This instance's `(axis, at, range)`: every component a plain
        number, the axis normalized, or `ParameterError` naming the
        class, the joint and the argument at fault."""
        axis = self._vector(node, values, self.axis, 'axis')
        anchor = self._vector(node, values, self.at, 'at')
        span = self._span(node, values)
        length = math.sqrt(sum(component ** 2 for component in axis))
        if length < _SNAP:
            raise self._refusal(
                node, 'axis',
                f'{self.axis!r} has no direction: an axis of zero length '
                f'states no line to move about')
        return tuple(component / length for component in axis), anchor, span

    def _refusal(self, node, argument, detail):
        from solid_node.parameters import ParameterError

        return ParameterError(
            f"{type(node).__name__}.{self.name}: {argument} -- {detail}")

    def _resolved(self, node, operand, argument):
        from solid_node.parameters import evaluate

        values = node.__dict__.get('_parameters', {})
        try:
            return evaluate(operand, values)
        except Exception as failure:
            raise self._refusal(
                node, argument,
                f'{operand!r} does not resolve against this instance '
                f'({type(failure).__name__}: {failure})') from None

    def _vector(self, node, values, declared, argument):
        """`declared` as three plain numbers.

        The whole argument may be a CALLABLE of one argument, called
        with the realized node: the case of a position that comes out
        of a library object the node builds from its parameters rather
        than out of a formula in the dimension algebra. Anything else is
        a sequence whose components are numbers, tokens or derived
        formulas.
        """
        if callable(declared):
            try:
                declared = declared(node)
            except Exception as failure:
                raise self._refusal(
                    node, argument,
                    f'the callable raised {type(failure).__name__}: '
                    f'{failure}') from None
        if isinstance(declared, (str, bytes)) or not _sized(declared, 3):
            raise self._refusal(
                node, argument,
                f'{declared!r} is not three components')
        components = []
        for component in declared:
            value = self._resolved(node, component, argument)
            if not _is_number(value):
                raise self._refusal(
                    node, argument,
                    f'component {value!r} is not a number')
            components.append(float(value))
        return tuple(components)

    def _span(self, node, values):
        declared = self.range
        if declared is None:
            return None
        if callable(declared):
            try:
                declared = declared(node)
            except Exception as failure:
                raise self._refusal(
                    node, 'range',
                    f'the callable raised {type(failure).__name__}: '
                    f'{failure}') from None
        if isinstance(declared, (str, bytes)) or not _sized(declared, 2):
            raise self._refusal(
                node, 'range', f'{declared!r} is not a (lo, hi) pair')
        bounds = []
        for bound in declared:
            value = self._resolved(node, bound, 'range')
            if not _is_number(value):
                raise self._refusal(
                    node, 'range', f'bound {value!r} is not a number')
            bounds.append(value)
        low, high = bounds
        if low > high:
            raise self._refusal(
                node, 'range',
                f'({low!r}, {high!r}) is reversed: a range is (lo, hi)')
        return (low, high)

    def arguments(self, node):
        """The resolved `(axis, at, range)` for `node`, resolving them
        now for a node the realization path never reached."""
        resolved = node.__dict__.setdefault('_joint_arguments', {})
        found = resolved.get(self.name)
        if found is None:
            found = resolved[self.name] = self.resolve(
                node, node.__dict__.get('_parameters', {}))
        return found

    ##############################################
    # Binding

    def _refuse_out_of_range(self, node, source):
        span = self.arguments(node)[2]
        if span is None:
            return
        value = source.value if isinstance(source, BoundPort) else source
        if not _is_number(value):
            # A symbolic binding -- an expression in the animation time,
            # a driver token -- has no value here to judge, and an
            # unbound source is bind()'s refusal to make, not this one's.
            return
        low, high = span
        if low <= value <= high:
            return
        raise JointRangeError(
            f"{_where(node)}: joint '{self.name}' declares the range "
            f"{low} to {high} {self.unit or 'units'}, and {value!r} is "
            f"outside it. A range refuses the binding rather than "
            f"clamping it, because a pose outside the joint's travel is "
            f"a mistake in what drives it.")

    def place(self, node, value):
        """Move `node` about this joint, absolutely.

        Carries the declared parent-frame axis and anchor into the
        node's own frame by inverting its rest placement, drops whatever
        a previous binding of this joint applied, and places the
        operations as motion -- innermost, before every rest operation,
        whatever lifecycle phase is current.
        """
        from solid_node.node.base import apply_motion

        axis, anchor, _span = self.arguments(node)
        local_axis, local_anchor = self._carry(node, axis, anchor)
        self.clear(node)
        applied = [apply_motion(node, operation) for operation
                   in self.placement(node, value, local_axis, local_anchor)]
        node.__dict__.setdefault('_joint_motion', {})[self.name] = applied

    def clear(self, node):
        """Drop the operations the previous binding of this joint
        applied.

        The recorded objects are a hint to remove, never an invariant:
        `_sweep` drops tagged operations by animator identity between
        runs and the test runner's checkpoint restore can replace the
        list wholesale, so an operation that is no longer there is
        simply not there.
        """
        previous = node.__dict__.get('_joint_motion', {}).pop(self.name, ())
        if not previous:
            return
        node.operations[:] = [
            operation for operation in node.operations
            if not any(operation is dropped for dropped in previous)]

    def _carry(self, node, axis, anchor):
        """The parent-frame `axis` and `anchor` in `node`'s own frame.

        Motion composes innermost -- before the placement the parent's
        `render()` applied -- so a joint stated in the parent's frame
        has to be carried through the inverse of that rest placement,
        which is the `into_local` every arm in the catalogue writes by
        hand. The rest placement is the node's non-motion operations
        composed in list order by premultiplication, through each
        operation's own `matrix()`: the framework's one seam for an
        operation's 4x4, which resolves its value through `as_number()`
        at access time.
        """
        import numpy as np

        matrix = np.eye(4)
        for operation in node.operations:
            if getattr(operation, '_motion', False):
                continue
            try:
                matrix = operation.matrix() @ matrix
            except TypeError as failure:
                raise ValueError(
                    f"{_where(node)}: joint '{self.name}' cannot be placed, "
                    f"because the rest operation {operation.serialized!r} "
                    f"carries a value that is not a number "
                    f"({failure}). A joint's axis and anchor are stated in "
                    f"the parent's frame and carried into the node's own by "
                    f"inverting that placement, so the placement has to be "
                    f"numeric; move the value into simulate().") from None
        inverse = np.linalg.inv(matrix)
        carried = inverse[:3, :3] @ np.array(axis, dtype=float)
        carried = carried / np.linalg.norm(carried)
        point = inverse @ np.array([anchor[0], anchor[1], anchor[2], 1.0])
        return (tuple(_snapped(float(value)) for value in carried),
                tuple(_snapped(float(value)) for value in point[:3]))

    def placement(self, node, value, axis, anchor):
        raise NotImplementedError


class Revolute(Joint):
    """A body turning about one line: `Revolute(axis, at, range, unit)`.

    Bound, it places `translate(-anchor)`, `rotate(value, axis)`,
    `translate(anchor)` in the node's own frame -- the two centring
    translations omitted entirely when the line runs through the node's
    placed origin, which is the case of a wheel on its own bearing.
    """

    coordinate_kind = RotationalPort
    default_unit = 'deg'

    def placement(self, node, value, axis, anchor):
        from solid_node.node.operations import Rotation, Translation

        centred = any(component != 0 for component in anchor)
        operations = []
        if centred:
            operations.append(
                Translation([-component for component in anchor], node))
        operations.append(Rotation(value, list(axis), node))
        if centred:
            operations.append(Translation(list(anchor), node))
        return operations


class Prismatic(Joint):
    """A body sliding along one line: `Prismatic(axis, at, range, unit)`.

    Bound, it places one translation of `value` along the carried unit
    axis. `at` does not affect the placement -- a translation along a
    line is the same wherever the line is taken to pass -- and is
    carried as the declared position of the slide, for a reader and for
    a later exporter.
    """

    coordinate_kind = TranslationalPort
    default_unit = 'mm'

    def placement(self, node, value, axis, anchor):
        from solid_node.node.operations import Translation

        translation = []
        for component in axis:
            if component == 0:
                # A plain numeric zero, not `value * 0`: an expression
                # multiplied by zero would put $t-shaped noise in two of
                # the three slots of every slide.
                translation.append(0)
            elif component == 1:
                translation.append(value)
            else:
                translation.append(value * component)
        return [Translation(translation, node)]


##############################################
# Enumeration

def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _sized(value, length):
    try:
        return len(value) == length
    except TypeError:
        return False


# Per-class cache of the declaration scan, exactly as
# `declared_drivers_of` keeps one: class attributes do not change at
# runtime, and a render asks this question for every node of the tree.
_declared_cache = {}


def declared_joints(node_class):
    """Every joint declared on `node_class`, by name.

    Reads the class dictionaries directly, so nothing is instantiated:
    a consumer can read a mechanism's freedoms off the class alone.
    Walked base-first so a subclass redeclaring an inherited joint wins.
    """
    cached = _declared_cache.get(node_class)
    if cached is None:
        found = {}
        for klass in reversed(node_class.__mro__):
            for name, value in vars(klass).items():
                if isinstance(value, Joint):
                    found[name] = value
        cached = _declared_cache[node_class] = found
    return cached


def resolve_declared_joints(node):
    """Resolve every joint argument of `node` against the instance.

    Called by the node constructor once the instance's parameters are
    resolved and its `check()` has run, and before any child is
    realized, so an argument that cannot resolve names the class, the
    joint and the argument at the earliest point a value could be wrong
    and a refused instance has realized nothing.
    """
    joints = declared_joints(type(node))
    if not joints:
        return
    values = node.__dict__.get('_parameters', {})
    resolved = node.__dict__.setdefault('_joint_arguments', {})
    for name, joint in joints.items():
        resolved[name] = joint.resolve(node, values)
