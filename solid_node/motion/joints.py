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

`Orbit` is the third, and it is not a lower pair at all: a body whose
ATTITUDE never changes while a point of it travels the circle that point
makes about a line -- a cycloidal disk on its eccentric, a connecting
rod's big end on the crank pin, the lower half of a parallelogram leg.
It owns one coordinate, an angle, and places ONE translation. Which
point of the body it carries is the joint's own argument, `carries`,
defaulting to the body's own placed origin; how far that point stands
from the line, and where on the circle it starts, are DERIVED from the
point and the line and are never typed, which is what lets a project
that may not write its bore centre as a literal write the joint at all.

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

A body may declare more than one freedom, and the ORDER they are
declared in is the order they compose in: the first declared is applied
closest to the body, the last declared is outermost, whatever order
their coordinates are bound in -- by hand, by a wiring, by a relation,
or by several relations a solver reached in an order the class body does
not show. A class read from top to bottom therefore reads a machine from
the body outward::

    class Chassis(AssemblyNode):
        roll  = Revolute(axis=(1, 0, 0), unit='deg')   # innermost
        pitch = Revolute(axis=(0, 1, 0), unit='deg')
        yaw   = Revolute(axis=(0, 0, 1), unit='deg')
        lift  = Prismatic(axis=(0, 0, 1), unit='mm')   # outermost

`declared_joints` is that order, and the whole of it: base classes
before the subclass, written order within a class body, a redeclared
joint keeping the position its base gave it. Hand-written motion on the
same node composes OUTSIDE the whole joint block, in call order among
itself (ADR-093).

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

from solid_node.motion.ports import (BoundPort, Coordinate, Port,
                                     RotationalPort, TranslationalPort,
                                     bind)


__all__ = ['Free', 'Joint', 'JointRangeError', 'Orbit', 'Prismatic',
           'Revolute', 'coordinates_of', 'declared_joints']


# How close to an exact 0, 1 or -1 a carried component has to be before
# it IS that value. Inverting a rest placement leaves floating-point
# residue -- an axis comes back as (0, 1, 6e-17) -- and whatever comes
# back is what the published document carries, so the residue is snapped
# away before anything reads it.
_SNAP = 1e-9

_MISSING = object()


class _OwnPlacedOrigin:
    """What an `Orbit` carries when its `carries` is left unstated: the
    body's OWN PLACED ORIGIN, the point the parent's `render()` put the
    node's origin at.

    A sentinel rather than a number, because the point is not known when
    a joint's arguments resolve -- the node's placement does not exist
    yet -- and because in the node's own frame it is exactly
    `(0, 0, 0)`, by definition and with no arithmetic, so carrying it
    through the inverted rest placement would only put floating-point
    residue in the commonest case.
    """

    def __repr__(self):
        return "the body's own placed origin"


_OWN_PLACED_ORIGIN = _OwnPlacedOrigin()


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


class Joint(Coordinate):
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
        # And the general form of the same fact: every coordinate this
        # joint owns, by the FULL name it answers to. A joint owning one
        # keeps `coordinate` as well and names it after the joint; a
        # joint owning several -- a `Free` -- has no `coordinate` at
        # all, which is what makes every "one coordinate" seam refuse it
        # rather than mis-handle it.
        self.coordinates = {self.name: self.coordinate}

    ##############################################
    # Declaration

    def _refuse_shadowing(self, owner, name):
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

    def __set_name__(self, owner, name):
        self._refuse_shadowing(owner, name)
        self.name = name
        self.owner = owner
        # The coordinate answers to the joint's own name: it is what
        # `declared_ports` reports, and what an error about the binding
        # has to be able to say.
        self.coordinate.name = name
        self.coordinate.owner = owner
        self.coordinates = {name: self.coordinate}

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
        class, the joint and the argument at fault.

        A subclass that declares a further argument -- an `Orbit`'s
        `carries` -- appends it here, through the same `_vector` path,
        so its refusals read like `at`'s by construction. `place`
        unpacks the first three and `_refuse_out_of_range` still reads
        index 2, so the range never moves.
        """
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
        """The resolved `(axis, at, range)` for `node` -- and whatever
        further argument the subclass declares after them -- resolving
        them now for a node the realization path never reached."""
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

        The whole placement goes in as ONE contiguous run at this
        joint's own slot: its index in `declared_joints(type(node))`,
        read straight off the per-class cache the enumerator already
        keeps. That is what makes the composition the declaration order
        of the class instead of the order the coordinates were bound in,
        and it is why re-binding one joint of several returns it to its
        own position rather than moving it outside its siblings.
        """
        from solid_node.node.base import apply_joint_motion

        anchor = self.arguments(node)[1]
        local_axes, local_points = self._carry(
            node, self.axes(node), self.carried_points(node, anchor))
        self.clear(node)
        slot = list(declared_joints(type(node))).index(self.name)
        applied = apply_joint_motion(
            node,
            list(self.placement(node, value, *local_axes, *local_points)),
            slot)
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

    def carried_points(self, node, anchor):
        """The parent-frame points this joint needs carried into the
        node's own frame, the anchor first.

        A joint that declares further points -- an `Orbit`'s `carries`
        -- returns them here and receives them, carried, as the extra
        arguments of its `placement`. They all ride the ONE inversion
        `_carry` already computes.
        """
        return (anchor,)

    def axes(self, node):
        """The parent-frame DIRECTIONS this joint needs carried into the
        node's own frame.

        One for every joint that turns or slides about a line, and the
        frame's own three for a joint that turns about all of them -- a
        `Free`. They ride the same single inversion the anchor and the
        carried points ride, and they arrive as the leading arguments of
        `placement`, in this order.
        """
        return (self.arguments(node)[0],)

    def _carry(self, node, axes, points):
        """Each of `axes` and each of `points`, stated in the parent's
        frame, in `node`'s own frame.

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
        local_axes = []
        for axis in axes:
            carried = inverse[:3, :3] @ np.array(axis, dtype=float)
            carried = carried / np.linalg.norm(carried)
            local_axes.append(tuple(_snapped(float(value))
                                    for value in carried))
        local = []
        for point in points:
            if point is _OWN_PLACED_ORIGIN:
                local.append((0.0, 0.0, 0.0))
                continue
            placed = inverse @ np.array([point[0], point[1], point[2], 1.0])
            local.append(tuple(_snapped(float(value))
                               for value in placed[:3]))
        return tuple(local_axes), tuple(local)

    def placement(self, node, value, axis, *points):
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



def _orbit_frame(axis, anchor, carried):
    """The two vectors an orbit turns in, and the radius it derives.

    `axis` a unit direction, `anchor` a point on that line and `carried`
    the point of the body that travels round it, all three in ONE frame.
    Splits `carried - anchor` into its component ALONG the line and its
    component ACROSS it: `across` is the radius vector, `quarter` is
    that vector turned a quarter turn about the line (the axis crossed
    with it), and both have length `radius`. Rodrigues then gives the
    displacement of the carried point at an angle `t` as
    `(cos t - 1) * across + sin t * quarter` -- a pure translation,
    carrying no rotation at any angle.

    The along-the-line component is projected out, which is why WHICH
    point of the line `anchor` names does not change the placement.
    """
    reach = tuple(float(point) - float(base)
                  for point, base in zip(carried, anchor))
    along = sum(component * direction
                for component, direction in zip(reach, axis))
    across = tuple(component - along * direction
                   for component, direction in zip(reach, axis))
    quarter = (axis[1] * across[2] - axis[2] * across[1],
               axis[2] * across[0] - axis[0] * across[2],
               axis[0] * across[1] - axis[1] * across[0])
    radius = math.sqrt(sum(component ** 2 for component in across))
    return across, quarter, radius


class Orbit(Joint):
    """A point of a body carried round one line, the body's attitude
    left alone: `Orbit(axis, at, carries, range, unit)`.

    `axis` and `at` mean exactly what a `Revolute`'s mean -- a direction
    and a point ON the line, in the parent's frame. `carries` is the
    point of the BODY that travels round that line, stated in the same
    frame and resolved the same way; left unstated it is the body's OWN
    PLACED ORIGIN, the point the parent's `render()` placed the node at.

    The coordinate is ONE angle, and it is rotational, although the
    placement it produces is a single translation: what the coordinate
    measures is an angle round the line, so a relation into an orbit
    inverts exactly as a relation into a `Revolute` does.

    **The radius and the phase are derived, never declared.** How far
    the carried point stands from the line, and where on the circle it
    starts, are consequences of the point and the line; a project that
    may not write its bore centre as a literal can still write the
    joint. A carried point ON the line derives a radius of zero -- the
    body would not move -- and is refused at the first binding, naming
    the node, the joint, the line, the point and the radius.
    """

    coordinate_kind = RotationalPort
    default_unit = 'deg'

    def __init__(self, axis, at=(0, 0, 0), carries=None, range=None,
                 unit=None):
        super().__init__(axis, at=at, range=range, unit=unit)
        self.carries = carries

    def __repr__(self):
        return (f'<Orbit {self.name} axis={self.axis!r} at={self.at!r} '
                f'carries={self.carries!r}>')

    def resolve(self, node, values):
        axis, anchor, span = super().resolve(node, values)
        if self.carries is None:
            # Not resolvable here, and not a number: the body's own
            # placed origin is not known until the body is placed.
            carried = _OWN_PLACED_ORIGIN
        else:
            carried = self._vector(node, values, self.carries, 'carries')
        return axis, anchor, span, carried

    def carried_points(self, node, anchor):
        return (anchor, self.arguments(node)[3])

    def placement(self, node, value, axis, anchor, carried):
        from solid_node.math import cos, sin
        from solid_node.node.operations import Translation

        across, quarter, radius = _orbit_frame(axis, anchor, carried)
        if radius <= _SNAP:
            raise ValueError(
                f"{_where(node)}: joint '{self.name}' carries a point "
                f"that lies ON its own axis, so binding it would move "
                f"nothing. In the node's own frame the axis is {axis} "
                f"through the anchor {anchor}, the carried point is "
                f"{carried}, and the radius they derive is {radius}. An "
                f"orbit's radius and phase are derived from a point and "
                f"a line, never declared, so name a point of the body "
                f"off that line with carries=, in the parent's frame.")

        # The framework's own DEGREE trigonometry: numeric for a plain
        # binding, and for a symbolic one the OpenSCAD builtins `cos`
        # and `sin`, which the parity corpus covers and the viewer
        # already evaluates (ADR-022). No new operation kind, and no
        # document key.
        turned = cos(value) - 1
        swept = sin(value)
        translation = []
        for reach, quarter_reach in zip(across, quarter):
            terms = []
            if abs(reach) > _SNAP:
                terms.append(turned * reach)
            if abs(quarter_reach) > _SNAP:
                terms.append(swept * quarter_reach)
            if not terms:
                # A plain numeric zero, not an expression multiplied by
                # zero: the reason `Prismatic` does this. A component
                # the circle does not reach would otherwise carry
                # $t-shaped noise in every orbit's published document.
                translation.append(0)
            elif len(terms) == 1:
                translation.append(terms[0])
            else:
                translation.append(terms[0] + terms[1])
        return [Translation(translation, node)]


class _BoundCoordinates:
    """What reading a joint that owns SEVERAL coordinates on an instance
    yields: a view of that node's own slots, one per coordinate.

    `chassis.pose.roll` is the coordinate's `BoundPort`, exactly as
    `wheel.turn` is a `Revolute`'s, and `chassis.pose.roll = 12` binds
    it through the one binding path every other coordinate is bound
    through and re-places the body. Holds nothing itself: the values
    live in the node's own port slots, so the view is built per read and
    two of them are interchangeable.
    """

    def __init__(self, joint, node):
        object.__setattr__(self, '_joint', joint)
        object.__setattr__(self, '_node', node)

    def _port(self, attribute):
        joint = object.__getattribute__(self, '_joint')
        return joint.coordinates.get(f'{joint.name}.{attribute}')

    def __getattr__(self, attribute):
        if attribute.startswith('_'):
            raise AttributeError(attribute)
        port = self._port(attribute)
        if port is None:
            raise AttributeError(_no_such_coordinate(
                object.__getattribute__(self, '_joint'), attribute))
        return port.__get__(object.__getattribute__(self, '_node'))

    def __setattr__(self, attribute, value):
        port = self._port(attribute)
        if port is None:
            raise AttributeError(_no_such_coordinate(
                object.__getattribute__(self, '_joint'), attribute))
        joint = object.__getattribute__(self, '_joint')
        node = object.__getattribute__(self, '_node')
        bind(port.__get__(node), value)
        # Any of the six changing re-places the WHOLE joint, from
        # whatever the others hold: that is what makes six coordinates
        # one joint rather than six, and it is why the composition never
        # depends on the order they were bound in.
        joint.place(node, None)

    def __repr__(self):
        joint = object.__getattribute__(self, '_joint')
        node = object.__getattribute__(self, '_node')
        return (f'<{type(joint).__name__} {joint.name} of '
                f'{getattr(node, "name", node)}: '
                f'{", ".join(sorted(joint.coordinates))}>')


def _no_such_coordinate(joint, attribute):
    return (f"'{joint.name}' owns no coordinate '{attribute}'. "
            f"{type(joint).__name__} owns "
            f"{', '.join(coordinates_of(joint))}, and each is reached "
            f"by its own name.")


class Free(Joint):
    """The six freedoms of a body with no parent to be jointed to:
    `Free(at, angle_unit, length_unit)`.

    A walking robot's chassis, a floating platform, anything whose pose
    against the world is STATED rather than constrained. MuJoCo's `free`
    and Modelica's `Joints.FreeMotion` are one element each, and so is
    this: ONE declaration owning SIX coordinates -- `roll`, `pitch` and
    `yaw` about the parent frame's three directions, and `x`, `y` and
    `z` along them -- reached as attributes of the joint read on an
    instance::

        class Chassis(AssemblyNode):
            pose = Free(angle_unit='deg', length_unit='mm')

        chassis.pose.roll = 12.0
        chassis.pose.z = 165.0

    Each of the six is an ordinary coordinate: bindable by assignment,
    nameable at either end of `drives`, readable by a driver or an
    expression, reported by `declared_ports`. What differs is the NAME
    it is reached by. **The naming rule:** a joint owning ONE coordinate
    names it after the joint; a joint owning SEVERAL names each
    `<joint name>.<coordinate name>` -- `pose.roll`. That one string is
    the port's name, the enumerator's key and the tail of a relation
    path, and there is no second spelling. It is not a Python
    identifier, so it is deliberately NOT a wiring keyword: such a
    coordinate is reached by assignment, by relation, and by a driver or
    an expression.

    **The composition is fixed by the contract**, innermost first, about
    the carried anchor::

        R(roll, x) . R(pitch, y) . R(yaw, z) . T(x, y, z)

    -- the roll closest to the body and the translation outermost, which
    as a matrix product acting on a point of the body is
    `T . Rz(yaw) . Ry(pitch) . Rx(roll)`. That is what the hexapod's
    chassis applies by hand and what its `_to_chassis` inverts for every
    leg solution in the model. The three directions are the PARENT
    frame's own, carried into the body's frame through the single
    inversion the anchor rides, so the three angles are an extrinsic
    x-y-z sequence -- the same rotation the aircraft convention states
    as intrinsic yaw, then pitch, then roll. Gimbal lock at
    `pitch = +-90` is real and inherited; `Spherical`, when it exists,
    is the quaternion-valued one.

    No `axis`: a free body turns about three directions, and they are
    the frame's own rather than an author's choice. No `range`: a
    floating body has no travel to bound. An UNBOUND coordinate places
    nothing -- no rotation, a plain zero offset -- while still reading
    as unbound, which is the rule every joint already obeys, stated per
    coordinate because a free joint's placement runs while some of its
    coordinates are unbound. The hexapod binds four of the six.
    """

    # The six, in the order they are declared, applied and reported.
    # The unit each carries is the declaration's own label for that
    # domain: with coordinates in two domains, one `unit` cannot serve.
    _ROTATIONS = ('roll', 'pitch', 'yaw')
    _TRANSLATIONS = ('x', 'y', 'z')

    def __init__(self, at=(0, 0, 0), angle_unit='deg', length_unit='mm',
                 **refused):
        if refused:
            raise TypeError(
                f"Free() takes at=, angle_unit= and length_unit=, and "
                f"nothing else; got {', '.join(sorted(refused))}=. A free "
                f"body turns about the three directions of the frame it is "
                f"stated in, so it declares no axis, and it has no travel to "
                f"bound, so it declares no range.")
        self.axis = None
        self.at = at
        self.range = None
        self.angle_unit = angle_unit
        self.length_unit = length_unit
        self.unit = None
        self.name = None
        self.owner = None
        # No `coordinate`: reading one off a `Free` is an AttributeError
        # rather than a wrong answer, and the three in-framework readers
        # of that seam all know about `coordinates` instead.
        self.coordinates = {}
        for short in self._ROTATIONS:
            self.coordinates[short] = RotationalPort(unit=angle_unit)
        for short in self._TRANSLATIONS:
            self.coordinates[short] = TranslationalPort(unit=length_unit)

    ##############################################
    # Declaration

    def __set_name__(self, owner, name):
        self._refuse_shadowing(owner, name)
        self.name = name
        self.owner = owner
        # The naming rule, applied where a one-coordinate joint names
        # its single coordinate after itself.
        self.coordinates = {
            f'{name}.{short}': port
            for short, port in self.coordinates.items()}
        for full, port in self.coordinates.items():
            port.name = full
            port.owner = owner

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return _BoundCoordinates(self, instance)

    def __set__(self, instance, value):
        raise AttributeError(
            f"'{self.name}' of {type(instance).__name__} owns "
            f"{len(self.coordinates)} coordinates and cannot be bound as "
            f"one value: it owns {', '.join(coordinates_of(self))}. Bind "
            f"one of them -- {type(instance).__name__.lower()}."
            f"{self.name}.{self._ROTATIONS[0]} = {value!r} -- or state a "
            f"relation into it.")

    def __getattr__(self, attribute):
        """A class-body read of one coordinate: `pose.roll.drives(...)`
        on the class declaring the joint."""
        if attribute.startswith('_'):
            raise AttributeError(attribute)
        coordinates = self.__dict__.get('coordinates') or {}
        name = self.__dict__.get('name')
        found = coordinates.get(f'{name}.{attribute}' if name else attribute)
        if found is None:
            raise AttributeError(_no_such_coordinate(self, attribute))
        return found

    def __repr__(self):
        return f'<Free {self.name} at={self.at!r}>'

    ##############################################
    # Arguments

    def resolve(self, node, values):
        """A `Free` resolves an `at` and nothing else: no axis to
        normalize and no range to order."""
        return None, self._vector(node, values, self.at, 'at'), None

    def axes(self, node):
        """The parent frame's own three unit directions, which `_carry`
        brings into the body's frame through the one inversion."""
        return ((1, 0, 0), (0, 1, 0), (0, 0, 1))

    ##############################################
    # Placement

    def placement(self, node, value, x_axis, y_axis, z_axis, anchor):
        """The run, in list order -- which is application order,
        innermost first, because the composition premultiplies.

        `value` is ignored: a free joint is re-placed in full from the
        values its six coordinates hold, whichever of them was just
        bound.
        """
        from solid_node.node.operations import Rotation, Translation

        bound = {short: self.coordinates[f'{self.name}.{short}']
                 .__get__(node)._value
                 for short in self._ROTATIONS + self._TRANSLATIONS}
        centred = any(component != 0 for component in anchor)
        operations = []
        if centred:
            operations.append(
                Translation([-component for component in anchor], node))
        for short, axis in zip(self._ROTATIONS, (x_axis, y_axis, z_axis)):
            if bound[short] is None:
                # An unbound coordinate places nothing: the rule an
                # unbound `Revolute` obeys by never being placed at all,
                # stated per coordinate because this placement runs
                # while some of the six are unbound.
                continue
            operations.append(Rotation(bound[short], list(axis), node))
        if centred:
            operations.append(Translation(list(anchor), node))
        offset = self._offset(bound, (x_axis, y_axis, z_axis))
        if offset is not None:
            operations.append(Translation(offset, node))
        return operations

    def _offset(self, bound, axes):
        """The one translation, or None when none of the three
        translational coordinates is bound.

        Each bound coordinate is a displacement along the carried
        direction of its own name -- the way a `Prismatic`'s value runs
        along its carried axis -- so a body whose parent turned it still
        floats against the PARENT's frame. A component no bound
        coordinate reaches is a plain numeric `0` rather than an
        expression multiplied by zero, for the reason a `Prismatic`'s
        is: two of the three slots of every floating body's published
        document would otherwise carry $t-shaped noise.
        """
        if all(bound[short] is None for short in self._TRANSLATIONS):
            return None
        offset = []
        for index in range(3):
            terms = []
            for short, axis in zip(self._TRANSLATIONS, axes):
                value = bound[short]
                component = axis[index]
                if value is None or component == 0:
                    continue
                terms.append(value if component == 1 else value * component)
            if not terms:
                offset.append(0)
                continue
            total = terms[0]
            for term in terms[1:]:
                total = total + term
            offset.append(total)
        return offset


##############################################
# Enumeration

def coordinates_of(joint):
    """The names of the coordinates `joint` owns, in declaration order.

    The one name each of them answers to: the joint's own for a joint
    that owns one, and `<joint>.<coordinate>` for each of a joint that
    owns several. What a refusal lists, and what a consumer reads a
    joint's freedoms by.
    """
    return tuple(joint.coordinates)


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
    """Every joint declared on `node_class`, by name, in DECLARATION
    order -- which is the order they COMPOSE in: the first declared is
    applied closest to the body and the last declared is outermost, so
    a class body read from top to bottom reads a machine from the body
    outward.

    Reads the class dictionaries directly, so nothing is instantiated:
    a consumer can read a mechanism's freedoms, and how they stack, off
    the class alone.

    The walk is base-first -- `reversed(node_class.__mro__)`, the MRO's
    own linearization -- so a base class's joints come before the
    subclass's, a class body's joints arrive in the order they were
    written (PEP 520), and a subclass redeclaring an inherited joint
    reuses its key and therefore KEEPS the base's position while taking
    its own axis, anchor, range and unit. That is not an accident of the
    implementation to be tidied later: this order is what the framework
    composes by, so a refactor that changed the walk would change where
    every machine's parts are.
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
