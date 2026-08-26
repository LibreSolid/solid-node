# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import functools
from collections.abc import Mapping
from solid2 import get_animation_time
from .base import _render_stack
from .internal import InternalNode
from .qualified import declared_drivers_of, driver_id


def _idempotent_render(render):
    """Wraps an AssemblyNode subclass render(): before rendering, sweep
    every node this assembly has ever animated and drop only the
    operations IT tagged (operation._animator is self), so each render
    expresses absolute kinematics for its instant instead of
    accumulating across re-renders.

    Sweeping by tag rather than removing by object identity matters:
    the test runner's per-instant checkpoint restore copies back
    whatever operations list was saved at test start, which can
    resurrect OLD operation objects this assembly already thought it
    had discarded. A tag-based sweep drops them anyway, by animator
    identity, regardless of which operation OBJECT currently sits in
    the list. It also means two independent assemblies animating the
    SAME node (e.g. a wheel spun by its axle and steered by the
    steering assembly) never disturb each other's operations: each
    only ever removes what it tagged."""

    @functools.wraps(render)
    def wrapped(self):
        if _render_stack and _render_stack[-1] is self:
            # Re-entrant call (a subclass render delegating to super):
            # the outer call already swept and is recording.
            return render(self)
        for node in getattr(self, '_animated_nodes', ()):
            node.operations[:] = [
                operation for operation in node.operations
                if getattr(operation, '_animator', None) is not self
            ]
        _render_stack.append(self)
        try:
            return render(self)
        finally:
            _render_stack.pop()

    wrapped._idempotent = True
    return wrapped


def _rendered_children(assembly):
    """The children to propagate a keyframe change into: the result of
    a fresh render, which is where they are created and bound, LINKED
    to their parent before anything recurses into them.

    Linking here is what makes qualification correct in this pass. A
    child's name is derived by its parent from the attribute holding it
    (base.py `_link_child`), so before linking both instances of one
    class still answer to the class name and a driver on either would
    qualify to the same bare id -- a silent collision, which is the
    defect instance qualification exists to remove. The scad and
    serializer passes have always linked before recursing; this one now
    does too, and linking is idempotent, so re-deriving the same
    attribute mapping changes nothing.

    A non-list/tuple render result carries no children to recurse into.
    serialize_node tolerates exactly that shape -- it keeps the partial
    node's representation for lifecycle validation to handle -- so the
    keyframe methods tolerate it too instead of raising TypeError while
    iterating a single node.
    """
    rendered = assembly.render()
    if type(rendered) not in (list, tuple):
        return ()
    for child in rendered:
        assembly._link_child(child)
    return rendered


def _entries_for(entries, child_name):
    """The entries addressed to `child_name`'s subtree, with the
    consumed leading segment stripped.

    A dotted entry is instance-scoped: `x_axis.motor` reaches only the
    child linked as `x_axis`, and arrives there as the local name
    `motor` its render() actually reads. An undotted entry -- a
    project driver bound by its bare name, and `time`, the one global
    -- propagates flat to everyone, exactly as it always has.
    """
    delivered = {}
    for name, value in entries.items():
        head, dot, rest = name.partition('.')
        if not dot:
            delivered[name] = value
        elif head == child_name:
            delivered[rest] = value
    return delivered


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


class _BoundState(Mapping):
    """The driver snapshot as render() reads it: a read-only view of
    the assembly's bound entries.

    A plain dict would answer a missing entry with a bare KeyError
    naming the key, which reads like a typo in the render code. The
    real cause is almost always that nobody bound that driver at all,
    so the message names the cure instead. The view is live rather than
    a copy, so it stays correct across the re-render set_state performs.
    """

    def __init__(self, states):
        self._states = states

    def __getitem__(self, name):
        try:
            return self._states[name]
        except KeyError:
            raise KeyError(f"no driver state '{name}' bound; bind it with "
                           f"set_state({name}=...)") from None

    def __iter__(self):
        return iter(self._states)

    def __len__(self):
        return len(self._states)


class AssemblyNode(InternalNode):
    """
    Represents a collection of components that can be moved relative to each other.
    This is an internal node that can contain instances of LeafNode or other
    internal nodes.
    The render method of this class returns a list of its child nodes.
    """

    _type = 'AssemblyNode'
    rigid = False

    def __init__(self, *args, **kwargs):
        # The bound driver snapshot: the named numeric values render()
        # reads through `state`. A machine that is not periodic depends
        # on several independent inputs, so this is a dict and not the
        # single `_time` it replaces -- time is one entry among them.
        self._states = {}
        super().__init__(*args, **kwargs)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        render = cls.__dict__.get('render')
        if render is not None and not getattr(render, '_idempotent', False):
            cls.render = _idempotent_render(render)

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
        """
        for name, value in states.items():
            self._validate_state(name, value)
        # A bare project-driver entry is the only thing that can turn
        # out to be ambiguous, and only a tree walk can say so: the
        # walk therefore records what it can roll back to, and only
        # when there is something a rollback could be needed for.
        bare = [name for name in states
                if '.' not in name and name != 'time']
        declared = {}
        saved = [] if bare else None
        self._receive_state(states, (), declared, saved)
        ambiguous = {name: declared[name] for name in bare
                     if len(declared.get(name, ())) > 1}
        if ambiguous:
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
            # ambiguity error rather than an unbound-read error raised
            # while cleaning up after it.
            if all(name in previous
                   for node, previous in saved
                   for name in declared_drivers_of(type(node))):
                self._receive_state({}, (), {}, None)
            detail = '; '.join(
                f"'{name}' could mean {', '.join(sorted(ids))}"
                for name, ids in sorted(ambiguous.items()))
            raise ValueError(
                f'ambiguous driver name in set_state: {detail}. Address '
                'the instance you mean by its qualified id, e.g. '
                f'set_state(**{{{sorted(next(iter(ambiguous.values())))[0]!r}'
                ': ...}).')

    def _receive_state(self, entries, path, declared, saved):
        """One node's share of a `set_state` propagation.

        Binds the entries addressed to this node (the undotted ones,
        after every ancestor stripped its own segment), records what
        this node declares under its qualified id, renders -- which is
        both where the expressions are rebuilt and where an unbound
        driver fails loudly -- and passes each child only what is
        addressed to it.
        """
        if saved is not None:
            saved.append((self, dict(self._states)))
        self._states.update(
            {name: value for name, value in entries.items()
             if '.' not in name})
        for name in declared_drivers_of(type(self)):
            # driver_id validates the path, so a driver reachable only
            # through a list-held child's `<attr>-<index>` name fails
            # here rather than emitting an id that parses as a
            # subtraction.
            declared.setdefault(name, []).append(driver_id(path, name))
        for child in _rendered_children(self):
            child._receive_state(_entries_for(entries, child.name),
                                 path + (child.name,), declared, saved)

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
        for child in _rendered_children(self):
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

    @property
    def state(self):
        """The bound driver snapshot this assembly's render() reads."""
        return _BoundState(self._states)

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
        try:
            return self._states['time']
        except KeyError:
            return get_animation_time()
