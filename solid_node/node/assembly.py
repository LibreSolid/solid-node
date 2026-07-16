# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import functools
from solid2 import get_animation_time
from .base import _render_stack
from .internal import InternalNode


def _idempotent_render(render):
    """Wraps an AssemblyNode subclass render(): before rendering, sweep
    every node this assembly has ever driven and drop only the
    operations IT tagged (operation._driver is self), so each render
    expresses absolute kinematics for its instant instead of
    accumulating across re-renders.

    Sweeping by tag rather than removing by object identity matters:
    the test runner's per-instant checkpoint restore copies back
    whatever operations list was saved at test start, which can
    resurrect OLD operation objects this assembly already thought it
    had discarded. A tag-based sweep drops them anyway, by driver
    identity, regardless of which operation OBJECT currently sits in
    the list. It also means two independent assemblies driving the
    SAME node (e.g. a wheel spun by its axle and steered by the
    steering assembly) never disturb each other's operations: each
    only ever removes what it tagged."""

    @functools.wraps(render)
    def wrapped(self):
        if _render_stack and _render_stack[-1] is self:
            # Re-entrant call (a subclass render delegating to super):
            # the outer call already swept and is recording.
            return render(self)
        for node in getattr(self, '_driven_nodes', ()):
            node.operations[:] = [
                operation for operation in node.operations
                if getattr(operation, '_driver', None) is not self
            ]
        _render_stack.append(self)
        try:
            return render(self)
        finally:
            _render_stack.pop()

    wrapped._idempotent = True
    return wrapped


class AssemblyNode(InternalNode):
    """
    Represents a collection of components that can be moved relative to each other.
    This is an internal node that can contain instances of LeafNode or other
    internal nodes.
    The render method of this class returns a list of its child nodes.
    """

    _type = 'AssemblyNode'
    rigid = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        render = cls.__dict__.get('render')
        if render is not None and not getattr(render, '_idempotent', False):
            cls.render = _idempotent_render(render)

    def set_keyframe(self, time):
        """Set a fixed time for keyframes and tests, propagating it
        down the tree so nested assemblies render numerically too."""
        self._time = time
        rendered = self.render()
        for child in rendered or ():
            child.set_keyframe(time)

    @property
    def time(self):
        """The $t variable, the animation time from 0 to 1"""
        try:
            return self._time
        except AttributeError:
            return get_animation_time()
