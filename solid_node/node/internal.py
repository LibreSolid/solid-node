# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from .base import AbstractBaseNode
from .ports import BoundPort
from solid2 import union


class InternalNode(AbstractBaseNode):
    """Internal nodes combine its children nodes in some way to make
    a node with several solids."""

    def connect(self, source, sink):
        """Bind `sink`'s value from `source`, converting through the
        sink's declared scale.

        Causal and immediate: this is sugar over an assignment, run
        while the owning render() runs, so a re-render under a new
        driver snapshot rebinds every port absolutely. There is no
        registry, no connection graph and no deferred resolution --
        the wiring is re-executed because the render code that states
        it runs again. Acausal connection (equations, solver
        orientation) is a separate, later design; nothing here should
        be read as a down payment on it.

        `source` is a bound port or a plain value; the value may be a
        symbolic animation expression, which flows through unresolved
        exactly as an operation value does.
        """
        if isinstance(source, BoundPort):
            if source.value is None:
                # An unbound source is a wiring order mistake -- the
                # emitting node has not run yet -- and silently
                # propagating None would surface it much later, as a
                # broken operation value.
                raise ValueError(
                    f'cannot connect {source.name} of '
                    f'{getattr(source.node, "name", source.node)}: it has '
                    'no value bound yet')
            value = source.value
        else:
            value = source
        if sink.scale is not None:
            value = value * sink.scale
        sink.value = value
        return sink

    @property
    def time(self):
        """Each internal node must implement property `time` to handle
        animation"""
        raise NotImplementedError(f"InternalNode subclass {self.__class__} "
                                  "must deal with animation time")

    @property
    def exact(self):
        if not self.children:
            raise RuntimeError(
                f'{self.name} exactness is unavailable before its children '
                'are linked by assemble()')
        return all(child.exact for child in self.children)

    def as_scad(self, children):
        """Renders a scad of the combined children"""
        scads = []

        for child in children:
            self._link_child(child)
            scads.append(child.assemble(self.root))
            self.files.update(child.files)

        # Assigned only AFTER the loop above: self.children is a plain
        # (non-private) list attribute, so setting it before deriving
        # names would make _attr_name_for's list-membership pass match
        # every child against IT -- including a child not referenced
        # by any real attribute of self, defeating the "keep the class
        # name" fallback (skill-repo improvements.md #16).
        self.children = children

        if len(scads) > 1:
            rendered = union()(scads)
        else:
            rendered = scads[0]

        return rendered

    def validate(self, rendered):
        """Check that rendered result is a list"""
        if type(rendered) not in (list, tuple):
            raise Exception(f"{self.__class__}.render() should return a list, "
                            f"not {type(rendered)}")

        for child in rendered:
            if not issubclass(type(child), AbstractBaseNode):
                raise Exception(f"{self.__class__}.render() returned invalid "
                                f"type {type(child)}")
            if type(child) is type(self):
                raise Exception(f"{self.__class__}.render() cannot return its "
                                "own type")
