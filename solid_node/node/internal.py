# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import functools

from .base import AbstractBaseNode
from .declarative import (StructureError, declared_child_nodes,
                          declared_children)
from .ports import bind
from solid2 import union


def _declarative_render(render):
    """Wraps an InternalNode subclass render(): when it returns None,
    the children are the realized declared children in declaration
    order minus those it omitted, so on a declarative class render()
    only positions and selects. A returned list is the author's and
    keeps its contract to the letter.

    Every tree walker -- as_scad, the serializer, the driver walk, state
    propagation -- calls render() and treats a non-list as "no
    children", so this is the one place that turns None into the list
    before any of them see it. On an assembly it sits INSIDE the
    lifecycle wrapper (`_lifecycle_render`), which sweeps first and
    runs simulate() after.

    Omission marks are cleared before the author's render() and read
    after it, so presence is decided afresh each render; the omitted set
    of the instance's first render is recorded and a later render that
    differs raises. An instance's parameters cannot change, so a
    difference can only come from time -- which structure must never
    depend on -- or from a bug. Re-entrant calls (a subclass render
    delegating to super) run the wrapped function bare: the outermost
    call owns the marks."""

    @functools.wraps(render)
    def wrapped(self):
        if self.__dict__.get('_rendering'):
            return render(self)
        declared = declared_child_nodes(self)
        for child in declared:
            child._omitted = False
        self.__dict__['_rendering'] = True
        try:
            rendered = render(self)
        finally:
            self.__dict__['_rendering'] = False
        if rendered is not None or not declared_children(type(self)):
            return rendered
        omitted = frozenset(child.name for child in declared
                            if child._omitted)
        recorded = self.__dict__.get('_omitted_record')
        if recorded is None:
            self.__dict__['_omitted_record'] = omitted
        elif recorded != omitted:
            raise StructureError(
                f"{type(self).__name__} '{self.name}' changed its structure "
                f"between renders: it first omitted "
                f"{sorted(recorded) or 'nothing'} and now omits "
                f"{sorted(omitted) or 'nothing'}. Structure may vary with "
                f"parameters, never with time; decide omit() from declared "
                f"parameters only.")
        return [child for child in declared if not child._omitted]

    wrapped._declarative = True
    return wrapped


def _render_declared(self):
    """The render() of a class that positions nothing: its declared
    children, exactly as declared."""
    return None


class InternalNode(AbstractBaseNode):
    """Internal nodes combine its children nodes in some way to make
    a node with several solids."""

    render = _declarative_render(_render_declared)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        render = cls.__dict__.get('render')
        if render is not None and not getattr(render, '_declarative', False):
            cls.render = _declarative_render(render)

    def connect(self, source, sink):
        """Bind `sink`'s value from `source`, converting through the
        sink's declared scale.

        Causal and immediate: this is sugar over an assignment, run
        in the owning simulate(), so a run under a new driver snapshot
        rebinds every port absolutely. There is no registry, no
        connection graph and no deferred resolution -- the wiring is
        re-executed because the simulate() that states it runs again.
        A parent's simulate() runs before any child's, so a child may
        read in its own simulate() what its parent bound. Called from
        a render() it binds once -- render() runs once -- and is
        reported as the deprecated form. Acausal connection
        (equations, solver orientation) is a separate, later design;
        nothing here should be read as a down payment on it.

        `source` is a bound port or a plain value; the value may be a
        symbolic animation expression, which flows through unresolved
        exactly as an operation value does.
        """
        return bind(sink, source)

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

        self._link_children(children)
        for child in children:
            scads.append(child.assemble(self.root))
            self.files.update(child.files)
            for path, names in child.scope.items():
                self.scope[path] = self.scope.get(path, frozenset()) | names

        # Assigned only AFTER the loop above: self.children is a plain
        # (non-private) list attribute, so setting it before deriving
        # names would make _attr_name_for's list-membership pass match
        # every child against IT -- including a child not referenced
        # by any real attribute of self, defeating the "keep the class
        # name" fallback (skill-repo improvements.md #16).
        self.children = children

        if len(scads) > 1:
            rendered = union()(scads)
        elif scads:
            rendered = scads[0]
        else:
            # A non-rigid assembly may contain no present parts. Keep the
            # ordinary composable result through assemble()/scad_code without
            # inventing geometry; FusionNode rejects this list in validate().
            rendered = union()()

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
