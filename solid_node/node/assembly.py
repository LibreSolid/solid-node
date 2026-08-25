# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import functools
from collections.abc import Mapping
from solid2 import get_animation_time
from .base import _render_stack
from .internal import InternalNode


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
    a fresh render, which is where they are created and bound.

    A non-list/tuple render result carries no children to recurse into.
    serialize_node tolerates exactly that shape -- it keeps the partial
    node's representation for lifecycle validation to handle -- so the
    keyframe methods tolerate it too instead of raising TypeError while
    iterating a single node.
    """
    rendered = assembly.render()
    if type(rendered) not in (list, tuple):
        return ()
    return rendered


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
        """
        for name, value in states.items():
            self._validate_state(name, value)
        self._states.update(states)
        for child in _rendered_children(self):
            child.set_state(**states)

    def clear_state(self, *names):
        """The inverse of set_state: drop the named driver values, or
        every one of them when called with no names, and propagate down
        the tree the same way.

        Re-rendering is what actually restores the unbound form. An
        operation records whatever value render() computed, so once a
        driver was a number every expression built from it had already
        collapsed and no symbolic form survived anywhere. The
        _idempotent_render sweep above drops exactly the operations
        this assembly applied before re-rendering, so the numeric ones
        are replaced while static placement applied outside any
        assembly render is left alone.
        """
        if names:
            for name in names:
                self._states.pop(name, None)
        else:
            self._states.clear()
        for child in _rendered_children(self):
            child.clear_state(*names)

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
        """
        try:
            return self._states['time']
        except KeyError:
            return get_animation_time()
