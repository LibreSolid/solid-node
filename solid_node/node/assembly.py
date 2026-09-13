# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import functools
from solid_node.scad_expression import get_animation_time
from . import phase as _phase
from .internal import InternalNode
from .qualified import declared_drivers_of, driver_id
from solid_node.motion.couplings import (clear_solved, refuse_reads,
                                         run_deferred, solve_relations)
from solid_node.motion.ports import declared_time


def _sweep(assembly):
    """Drop every operation this assembly tagged on the nodes it has
    ever animated, and only those (operation._animator is assembly), so
    the run that follows expresses absolute kinematics for its instant
    instead of accumulating across runs.

    Sweeping by tag rather than removing by object identity matters:
    the test runner's per-instant checkpoint restore copies back
    whatever operations list was saved at test start, which can
    resurrect OLD operation objects this assembly already thought it
    had discarded. A tag-based sweep drops them anyway, by animator
    identity, regardless of which operation OBJECT currently sits in
    the list. It also means two independent assemblies animating the
    SAME node (a wheel spun by its axle and steered by the steering
    assembly) never disturb each other's operations: each only ever
    removes what it tagged."""
    for node in getattr(assembly, '_animated_nodes', ()):
        node.operations[:] = [
            operation for operation in node.operations
            if getattr(operation, '_animator', None) is not assembly
        ]


def _rest(assembly, render):
    """The children at rest: the author's render(), run once.

    The first run decides what the render is. One that read no driver,
    no time and no port built the machine at rest: its operations are
    untagged so the sweep never touches them, and its result is kept,
    so later calls never run the author's code again -- structure and
    rest placement are the instance's, exactly as its parameters are.
    One that did read is a legacy render, written when render() was
    the only method there was: the instance keeps re-running it under
    every binding with its operations tagged and swept, as it always
    did, and the class is named once in a FutureWarning."""
    if '_rest' in assembly.__dict__:
        return assembly.__dict__['_rest']
    phase = _phase.push(assembly, _phase.RENDER)
    try:
        rendered = render(assembly)
    finally:
        _phase.pop()
    if assembly.__dict__.get('_legacy_render'):
        return rendered
    if phase.read is None:
        for operation in phase.applied:
            del operation._animator
        assembly.__dict__['_rest'] = rendered
        return rendered
    assembly.__dict__['_legacy_render'] = True
    _phase.warn_legacy_render(assembly, phase.read)
    return rendered


def _linked(children):
    """`children` as a tuple to walk, or `()` for a non-list/tuple render
    result -- `serialize_node` tolerates exactly that shape (it keeps the
    partial node's representation for lifecycle validation to handle),
    so every walk here tolerates it too instead of raising TypeError
    while iterating a single node."""
    return children if type(children) in (list, tuple) else ()


def _run_phase(assembly, render, enumeration):
    """One assembly's own phase, in its stated order: sweep, rest, LINK
    (so a message about a child, or a path through one, resolves by path
    rather than falling back to the child's class name), clear what this
    assembly bound last run, the author's simulate(), then this
    instance's own relations and wirings attempted together -- what that
    attempt cannot reach is deferred to `enumeration` rather than
    refused. All of it happens while the phase is still this assembly's,
    so every motion it causes carries its tag and is swept before its
    next run.

    Returns the children (linked already), and marks the assembly as
    having run in THIS enumeration -- unless its render is a LEGACY one:
    a render that reads a driver has to re-run in full on every call by
    definition, so it carries no mark and pays for it, exactly as it
    always has.
    """
    _sweep(assembly)
    children = _rest(assembly, render)
    assembly._link_children(_linked(children))
    phase = _phase.push(assembly, _phase.SIMULATE)
    try:
        clear_solved(assembly)
        assembly.simulate()
        solve_relations(assembly, enumeration)
    finally:
        _phase.pop()
    # Everything THIS phase bound -- the author's own simulate() included
    # (`ports.bind` -> `phase.note_bound`), whether or not this assembly
    # states any relation of its own -- is what the assembly's NEXT
    # phase clears (`couplings.clear_solved`), so a rest-default joint's
    # value is dropped with its swept motion instead of surviving it.
    assembly.__dict__['_solver_bound'] = phase.bound
    if not assembly.__dict__.get('_legacy_render'):
        assembly.__dict__['_ran_in_enumeration'] = enumeration
    return children


def _drivable(node):
    """Whether `node` is an assembly whose render() carries the
    lifecycle -- the one thing that distinguishes it from a leaf for the
    enumeration's own drive, which has nothing to do at a leaf: a leaf
    has no simulate phase and the WALKER (assemble(), the serializer)
    reads its geometry on its own pass, afterwards."""
    return getattr(type(node).render, '_idempotent', False)


def _finish_enumeration(enumeration):
    """The pass's own fixpoint, once every assembly's phase in its
    subtree has run: propagate over what was deferred, refuse what is
    still unreached, then refuse a recorded read whose coordinate was
    bound after all -- exactly the couplings capability's own order."""
    run_deferred(enumeration)
    refuse_reads(enumeration)


def _lifecycle_render(render):
    """Wraps an AssemblyNode subclass render() into the lifecycle every
    tree walker sees as one call.

    The first `render()` reached with no ENUMERATION already open OWNS
    it: it opens the pass, drives its own phase and then every assembly
    in the subtree it renders -- parents before children, declaration
    order among siblings, over the children each one's own `_rest`
    returned -- before running the pass's fixpoint and returning. A
    `render()` reached while an enumeration is already open either IS
    that drive (a child the owning call is descending into) or has
    already run in this one (the mark set by `_run_phase`, consumed here
    without re-running the phase) -- which is what makes a node's phase
    run exactly once per enumeration however many times the walkers that
    follow call render() on it (`whole-tree-fixpoint`)."""

    @functools.wraps(render)
    def wrapped(self):
        phase = _phase.current()
        if phase is not None and phase.assembly is self:
            # Re-entrant call (a subclass render delegating to super):
            # the outer call owns the phase.
            return render(self)

        enumeration = _phase.current_enumeration()
        if (enumeration is not None
                and self.__dict__.get('_ran_in_enumeration') is enumeration):
            # A child the OWNING call's own drive is descending into,
            # already run this enumeration: return its rest children
            # without re-running its phase (design.md step 11).
            #
            # This is scoped to an enumeration that is STILL open, on
            # purpose, not to "the last one opened, open or since
            # closed": several call sites bind a coordinate directly and
            # call render() again with no enumeration in between --
            # `SiteOrbitRepeatDerivedPhaseTest` sets a joint by hand
            # twice; `qualified.drive_tree` (the serializer's symbolic
            # pass, the loader's default binding) writes a node's
            # snapshot directly, not through set_state -- and a mark
            # compared against a MERELY-remembered last enumeration would
            # skip re-simulating against the fresh value, reading a
            # stale pose instead of a wrong error. A design that kept the
            # optimization across such a call would need a single choke
            # point where every write to a node's bound coordinates and
            # snapshot is known, which `bind`'s callers do not currently
            # give it; see evidence.md, task 8's cost report and the
            # implementation report for this deviation from design.md
            # step 11's stated optimization, made in favour of never
            # returning a pose that does not match what was just bound.
            return self.__dict__['_rest']

        owns = enumeration is None
        if owns:
            enumeration = _phase.open_enumeration()
        try:
            children = _run_phase(self, render, enumeration)
            for child in _linked(children):
                if _drivable(child):
                    child.render()
            if owns:
                _finish_enumeration(enumeration)
        finally:
            if owns:
                _phase.close_enumeration()
        return children

    wrapped._idempotent = True
    return wrapped


def _rest_children(assembly):
    """The children a REST-ONLY walk descends into: `_rest`'s own
    idempotent render, LINKED, with no phase and no enumeration touched.

    This is what `set_state`/`clear_state` walk to DELIVER a snapshot
    over the tree before enumerating: `probe_state_order.py` measured
    that a walk which renders (and therefore simulates) as it delivers
    leaves a descendant's own phase running one binding behind the one
    just requested, because `set_state` used to bind a node's entries
    only immediately before rendering that node. Reaching the ORIGINAL
    render underneath the lifecycle wrapper (`functools.wraps` sets
    `__wrapped__`) means this walk never opens a phase or an
    enumeration -- structure only, exactly as `_rest` always was.
    """
    original = getattr(type(assembly).render, '__wrapped__',
                       type(assembly).render)
    children = _linked(_rest(assembly, original))
    assembly._link_children(children)
    return children


def _entries_for(entries, child_name, consumed=()):
    """The entries addressed to `child_name`'s subtree, with the
    consumed leading segment stripped.

    A dotted entry is instance-scoped: `x_axis.motor` reaches only the
    child linked as `x_axis`, and arrives there as the local name
    `motor` its render() actually reads. An undotted entry -- a
    project driver bound by its bare name, and `time`, the one global
    -- propagates flat to everyone, exactly as it always has.

    `consumed` are the names THIS node already bound as its own joint
    coordinates. A dotted one of those -- `pose.roll`, a coordinate of a
    joint owning several -- is dropped rather than forwarded: its head
    is the JOINT's name, not a child's, and forwarding it would address
    a child that happened to share the name.
    """
    delivered = {}
    for name, value in entries.items():
        head, dot, rest = name.partition('.')
        if dot and name in consumed:
            continue
        if not dot:
            delivered[name] = value
        elif head == child_name:
            delivered[rest] = value
    return delivered


class CoordinateDelivery:
    """`set_state`'s delivery of JOINT COORDINATE entries, under a
    running root and nowhere else (OpenSpec change
    ``run-owns-the-coordinates``).

    Under `Time.running()` a bound name may be the qualified id of a
    joint coordinate the tree publishes -- `first.turn`,
    `chassis.pose.roll` -- and it is delivered to the node that OWNS the
    coordinate, a leaf included, and bound through `set_coordinate`, the
    one binding path a coordinate assignment takes. So the joint's
    declared range and placement apply exactly as for any binding.

    `binder` is what to record as having bound them: the RUNNING
    SIMULATION when a run owns the tree, so the solver recognizes its
    slots, and `None` when a caller binds one by hand. It wraps the
    BINDING and nothing else -- never the enumeration `set_state` runs
    afterwards, whose author bindings must stay the author's (design.md
    sections 4.5 and 7.7).

    `saved` is what a REFUSED binding rolls back to: the value, the
    binder and the freshness marks each slot held, restored in reverse
    and the joint re-placed from what its coordinates then hold, so a
    rejected `set_state` leaves no half-posed tree.
    """

    __slots__ = ('binder', 'saved')

    def __init__(self, binder):
        self.binder = binder
        self.saved = []

    @staticmethod
    def names(node_class):
        """Every joint coordinate `node_class` declares, by the name the
        port enumeration reports it under."""
        from solid_node.motion.joints import coordinates_of, declared_joints

        found = []
        for joint in declared_joints(node_class).values():
            found.extend(coordinates_of(joint))
        return found

    def deliver(self, node, entries, path, declared):
        """Bind the entries naming `node`'s OWN joint coordinates, and
        record their ids beside the driver ids so the unknown and
        ambiguous checks cover them. Returns the names consumed."""
        from solid_node.motion.ports import (binding_as, get_coordinate,
                                             set_coordinate)

        consumed = []
        for name in self.names(type(node)):
            if name not in entries:
                continue
            declared.setdefault(name, []).append(driver_id(path, name))
            slot = get_coordinate(node, name)
            self.saved.append((node, name, slot, slot._value, slot.binder,
                               slot._enum_marker, slot._bound_by))
            with binding_as(self.binder):
                set_coordinate(node, name, entries[name])
            consumed.append(name)
        return consumed

    def restore(self):
        from solid_node.motion.joints import declared_joints
        from solid_node.motion.ports import get_coordinate

        while self.saved:
            node, name, slot, value, binder, marker, bound_by = self.saved.pop()
            slot._value = value
            slot.binder = binder
            slot._enum_marker = marker
            slot._bound_by = bound_by
            for joint in declared_joints(type(node)).values():
                if name not in joint.coordinates:
                    continue
                held = [get_coordinate(node, owned)._value
                        for owned in joint.coordinates]
                if any(one is None for one in held):
                    joint.clear(node)
                else:
                    joint.place(node,
                                held[0] if len(held) == 1 else None)
                break


def _coordinate_delivery(node):
    """The coordinate delivery `set_state` performs from `node`, or
    `None` under any root but a running one -- where a joint coordinate
    id is refused exactly as an undeclared name is, because outside a
    run a coordinate has no history for a snapshot entry to carry."""
    root = top_of(node)
    base = declared_time(type(root))
    if base is None or base.mode != 'running':
        return None
    return CoordinateDelivery(root.__dict__.get('_run_binder'))


def _names_for(names, child_name):
    """`_entries_for` for clear_state's name list. `None` means every
    entry, and stays `None` all the way down."""
    if names is None:
        return None
    delivered = []
    for name in names:
        head, dot, rest = name.partition('.')
        if not dot:
            delivered.append(name)
        elif head == child_name:
            delivered.append(rest)
    return tuple(delivered)


class AssemblyNode(InternalNode):
    """
    Represents a collection of components that can be moved relative to each other.
    This is an internal node that can contain instances of LeafNode or other
    internal nodes.
    The render method of this class returns a list of its child nodes.
    """

    _type = 'AssemblyNode'
    rigid = False

    # A methodless assembly renders its declared children through the
    # same lifecycle a subclass render() gets, so nothing is special
    # about having nothing to position.
    render = _lifecycle_render(InternalNode.render)

    def __init__(self, *args, **kwargs):
        # The bound driver snapshot: the named numeric values render()
        # reads through `state`. A machine that is not periodic depends
        # on several independent inputs, so this is a dict and not the
        # single `_time` it replaces -- time is one entry among them.
        self._states = {}
        super().__init__(*args, **kwargs)

    def __init_subclass__(cls, **kwargs):
        # InternalNode's hook runs first and wraps a subclass render()
        # for the declarative substitution; the lifecycle goes outside
        # it, so the order is sweep, clear omissions, author's render(),
        # author's simulate().
        super().__init_subclass__(**kwargs)
        render = cls.__dict__.get('render')
        if render is not None and not getattr(render, '_idempotent', False):
            cls.render = _lifecycle_render(render)

    def simulate(self):
        """Move the machine for the current instant.

        Run by the framework after render() on every enumeration of
        this assembly's children, under whatever binding is current:
        symbolic `$t` when nothing is bound, plain numbers under
        set_state, set_keyframe, the test runner, the snapshot tool and
        the simulator. This is where drivers, `self.time` and ports are
        read and bound, and every operation applied here is motion:
        innermost on the part's chain, before the rest placement
        render() gave it, and swept before the next run so the pose is
        absolute. The base does nothing, so `super().simulate()`
        chains; a part that does not move needs no simulate() at all.
        Structure is not decided here: omit() raises.
        """

    def set_state(self, **states):
        """Bind named driver values for this instant, propagating them
        down the tree so nested assemblies render numerically too.

        Entries MERGE into the current snapshot rather than replacing
        it: set_keyframe(t) is this method with a single entry, and it
        must go on touching nothing but time. A stepping loop that
        binds a full snapshot every tick is unaffected either way.

        An entry is addressed either to the whole tree or to one
        instance in it. A dotted name is an instance-qualified driver
        id -- `set_state(**{'x_axis.motor': 8000})`, passed as a
        mapping because a dotted name is not a Python identifier --
        and reaches only that instance's subtree, so two instances of
        one class hold independent values for their same-named driver.
        A bare name propagates flat, which is the stage-2 form and
        still exactly right while the tree holds only one driver by
        that name; when it holds two, binding fails naming both
        qualified ids rather than quietly giving them one value.
        `time` is the one entry that is global by contract, and never
        needs qualifying.

        Every other entry has to NAME a declared driver -- a bare name
        some declaration in the tree bears, or a qualified id the tree
        publishes -- and binding fails when it does not. Nothing could
        read such an entry: a driver is read as an attribute of the
        node that declares it, so a name with no declaration behind it
        binds a value that is unreachable, and the mistake would
        surface later, somewhere else, as a DIFFERENT driver's
        unbound-read error.
        """
        for name, value in states.items():
            self._validate_state(name, value)
        # Only a tree walk can say what is declared, so the walk
        # records what it can roll back to whenever there is a name to
        # judge -- which is every entry except the one global.
        judged = [name for name in states if name != 'time']
        declared = {}
        saved = [] if judged else None
        coordinates = _coordinate_delivery(self)
        self._receive_state(states, (), declared, saved, coordinates)
        publishes = {identifier
                     for ids in declared.values() for identifier in ids}
        unknown = [name for name in judged
                   if (name not in publishes if '.' in name
                       else name not in declared)]
        ambiguous = {name: declared[name] for name in judged
                     if '.' not in name and len(declared.get(name, ())) > 1}
        if unknown:
            self._undo(saved, coordinates)
            known = ', '.join(sorted(publishes)) or 'none'
            raise ValueError(
                f'undeclared driver name in set_state: '
                f'{", ".join(repr(name) for name in sorted(unknown))}. '
                f'A bound name must name a declared driver, because a '
                f'driver is read as an attribute of the node declaring '
                f'it; declared: {known}.')
        if ambiguous:
            self._undo(saved, coordinates)
            detail = '; '.join(
                f"'{name}' could mean {', '.join(sorted(ids))}"
                for name, ids in sorted(ambiguous.items()))
            raise ValueError(
                f'ambiguous driver name in set_state: {detail}. Address '
                'the instance you mean by its qualified id, e.g. '
                f'set_state(**{{{sorted(next(iter(ambiguous.values())))[0]!r}'
                ': ...}).')
        # The snapshot is delivered over the whole tree AT REST, above --
        # `_receive_state` never renders. Only now, once every node's
        # entries are in place, does ONE enumeration run from this node,
        # so a descendant's own phase simulates against the binding just
        # requested rather than the previous one (`probe_state_order.py`,
        # `whole-tree-fixpoint`).
        self.render()

    def _undo(self, saved, coordinates=None):
        """Restore the snapshot every node held before a binding this
        call is about to refuse, so a rejected `set_state` leaves no
        half-bound tree -- and, under a running root, every joint
        coordinate this call bound as well."""
        if coordinates is not None:
            coordinates.restore()
        for node, previous in saved:
            node._states.clear()
            node._states.update(previous)
        # Re-render under the restored snapshot, so no operation
        # survives from the pose that was never accepted. Unless the
        # snapshot restored to has holes: a tree nobody had bound
        # could not be rendered before this call either, and
        # inventing a value to re-render it with is exactly what the
        # unbound contract forbids -- so its stale operations wait
        # for whatever renders it next, and the caller gets the
        # binding error rather than an unbound-read error raised
        # while cleaning up after it.
        if all(name in previous
               for node, previous in saved
               for name in declared_drivers_of(type(node))):
            self._receive_state({}, (), {}, None, None)

    def _receive_state(self, entries, path, declared, saved,
                       coordinates=None):
        """One node's share of a `set_state` propagation.

        Binds the entries addressed to this node (the undotted ones,
        after every ancestor stripped its own segment), records what
        this node declares under its qualified id, and passes each child
        only what is addressed to it -- over the tree AT REST
        (`_rest_children`), never simulating: an unbound driver is
        caught by the READ it fails loudly at, once the single
        enumeration `set_state` runs afterward reaches it, not by this
        delivery walk.
        """
        if saved is not None:
            saved.append((self, dict(self._states)))
        # A name this node's own JOINT reports is this node's coordinate
        # and not a snapshot entry: it is bound through `set_coordinate`
        # before the dotted split, so `chassis.pose.roll` reaches
        # `pose.roll` on `chassis` and never becomes an attribute of
        # that name. Under any other root `coordinates` is None and
        # nothing here changes.
        consumed = ()
        if coordinates is not None:
            consumed = coordinates.deliver(self, entries, path, declared)
        self._states.update(
            {name: value for name, value in entries.items()
             if '.' not in name and name not in consumed})
        for name in declared_drivers_of(type(self)):
            # driver_id validates the path, so a driver reachable only
            # through a list-held child's `<attr>-<index>` name fails
            # here rather than emitting an id that parses as a
            # subtraction.
            declared.setdefault(name, []).append(driver_id(path, name))
        for child in _rest_children(self):
            child._receive_state(
                _entries_for(entries, child.name, consumed),
                path + (child.name,), declared, saved, coordinates)

    def clear_state(self, *names):
        """The inverse of set_state: drop the named driver values, or
        every one of them when called with no names, and propagate down
        the tree the same way -- accepting qualified names exactly as
        set_state does, so one instance can be cleared while its
        sibling keeps its snapshot.

        Re-rendering is what actually restores the unbound form. An
        operation records whatever value render() computed, so once a
        driver was a number every expression built from it had already
        collapsed and no symbolic form survived anywhere. The
        _idempotent_render sweep above drops exactly the operations
        this assembly applied before re-rendering, so the numeric ones
        are replaced while static placement applied outside any
        assembly render is left alone.
        """
        self._receive_clear(tuple(names) if names else None)
        # As in set_state: deliver over the tree at rest first (above),
        # then enumerate once.
        self.render()

    def _receive_clear(self, names):
        """One node's share of a `clear_state` propagation. `None` is
        "every entry" and stays `None` all the way down; a tuple is the
        names still addressed to this subtree."""
        if names is None:
            self._states.clear()
        else:
            for name in names:
                if '.' not in name:
                    self._states.pop(name, None)
        for child in _rest_children(self):
            child._receive_clear(_names_for(names, child.name))

    def _validate_state(self, name, value):
        """A snapshot entry is a plain number, exactly as strictly as
        as_number() judges an operation value.

        Binding an expression instead would defeat the point of a
        snapshot: the pose would stop being a function of the driver
        values and start depending on whatever the expression closed
        over.
        """
        try:
            self.as_number(value)
        except TypeError:
            raise TypeError(f"state '{name}' must be a plain number, "
                            f"not {value!r}") from None

    def set_keyframe(self, time):
        """Set a fixed time for keyframes and tests, propagating it
        down the tree so nested assemblies render numerically too.

        Exactly the time-only surface over the snapshot: time is one
        driver among several, and keyframing binds that one entry.
        """
        self.set_state(time=time)

    def clear_keyframe(self):
        """The inverse of set_keyframe: drop the fixed time so this
        assembly renders against solid2's symbolic $t again, leaving
        any other bound driver in place."""
        self.clear_state('time')

    @property
    def time(self):
        """The $t variable, the animation time from 0 to 1.

        One entry of the snapshot, with the ADR-008 fallback: an
        assembly nobody bound a time on still animates symbolically,
        which is what the build and viewer paths depend on. Only time
        falls back -- any other unbound driver fails loudly, because a
        default invented here would bind the simulation layer to a
        contract it never chose.

        `time` is the one entry that is global by contract: it
        propagates flat and unqualified to every descendant, and never
        needs an instance path. What it MEANS is the binder's choice --
        a keyframe binds the normalized 0..1 fraction, a running
        simulation binds the stepped clock in seconds -- and this
        property just reports whatever was bound.
        """
        return read_time(self)


def read_time(node):
    """What `node.time` reads: the one reader behind the base property
    and a `Time` declaration's descriptor (OpenSpec `declared-time-base`).

    Bound, the snapshot entry -- whatever the binder stated, which is
    seconds under a declared time base and the 0..1 fraction otherwise.
    Unbound, the symbolic timeline scaled by the ROOT's time base:
    `$t * loop` when the root of the linked tree declares one, bare `$t`
    when it does not, so a descendant reads exactly what its root reads
    without any state being propagated to make it so.

    The walk up is where a stray declaration is caught: a node strictly
    below the root whose class declares a `Time` would scale its own
    subtree differently, and the read refuses naming both nodes.  An
    assembly that IS the root of the tree it is read in -- a component
    under test, or loaded alone -- uses its own declaration.

    The walk relies on the link every tree walker makes before it
    recurses (`_link_child` from the scad, serializer and state passes);
    a bare `render()` links nothing, by contract, so a child rendered by
    hand before any walker reached it is its own root for that read.
    """
    _phase.note_read('read time', 'time')
    try:
        return node._states['time']
    except KeyError:
        pass
    root = node
    parent = getattr(root, '_parent', None)
    while parent is not None:
        if declared_time(type(root)) is not None:
            raise TypeError(
                f"'{root.name}' ({type(root).__name__}) declares a time "
                f"base below the root '{top_of(root).name}' "
                f"({type(top_of(root)).__name__}): the time base is the "
                f"root's to declare, and every assembly below it reads "
                f"the root's. Declare Time on the root, or drop it from "
                f"the component.")
        root = parent
        parent = getattr(root, '_parent', None)
    base = declared_time(type(root))
    if base is None or base.loop is None:
        # No loop: an undeclared root, or the RUNNING base, whose
        # elapsed seconds never wrap and have no symbolic form until a
        # compiled program is published. Both read bare `$t`, so a
        # running root's document is the document an undeclared root
        # publishes (OpenSpec change ``run-owns-the-coordinates``).
        return get_animation_time()
    return get_animation_time() * base.loop


def top_of(node):
    """The root of the linked tree `node` hangs in."""
    while getattr(node, '_parent', None) is not None:
        node = node._parent
    return node
