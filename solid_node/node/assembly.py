# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import functools
from solid2 import get_animation_time
from .base import _render_stack
from .internal import InternalNode


def _idempotent_render(render):
    """Wraps an AssemblyNode subclass render(): before rendering, every
    node a previous render touched kinematically is restored to its
    pre-render operations, so each render expresses absolute kinematics
    for its instant instead of accumulating across re-renders."""

    @functools.wraps(render)
    def wrapped(self):
        if _render_stack and _render_stack[-1] is self:
            # Re-entrant call (a subclass render delegating to super):
            # the outer call already restored and is recording.
            return render(self)
        if not hasattr(self, '_prerender_operations'):
            self._prerender_operations = {}
        for node, operations in self._prerender_operations.items():
            node.operations[:] = list(operations)
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
        """Set a fixed time for keyframes and tests"""
        self._time = time
        self.render()

    @property
    def time(self):
        """The $t variable, the animation time from 0 to 1"""
        try:
            return self._time
        except AttributeError:
            return get_animation_time()
