# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The structure a class body declares: children, and how a body is
recognized as one.

A node class body declares three things -- tree structure, parameter
propagation and ports -- and the framework derives everything else. This
module holds the first. `solid_node.parameters` holds the second, and
`ports` next door the third; `DriverDeclaration` in `qualified.py` is the
precedent all of them follow: a declaration is class metadata shared by
every instance, read off the instance as a plain value, enumerable off the
class without constructing anything.

A node constructed inside a node class body is a DECLARATION of a child,
never an instance: an instance would be one object mutated by every
parent, which is the empirical fact that forces this whole model.
`AbstractBaseNode.__new__` asks `in_class_body()` and returns a
`ChildDeclaration` instead; each parent instance realizes its own child at
construction, top-down, with the tokens it was handed resolved against its
own values. Resolving them is the one service this module takes from the
parameter layer, through `evaluate`.

`NodeMeta` is what makes the class-body question answerable. Its
`__prepare__` hands the class statement a namespace of a private type,
and a node constructor recognizes an executing body by finding that
namespace as the locals of a frame on its stack. The namespace's own
identity is the signal rather than a counter kept in step by `__new__`,
because a body that raises -- a dimension error, on purpose -- never
reaches the metaclass `__new__`, and a counter would stay stuck. The
same namespace names each declaration the moment it is assigned, which
is what lets a dimension error in the next line of the body say `bore`
and `pressure_angle` instead of two anonymous tokens. It names a
parameter and a child alike, which is why it knows the parameter layer's
`Declaration` type.
"""

import sys

from solid_node.parameters import (Declaration, ParameterError,
                                   declared_parameters, evaluate)


class StructureError(RuntimeError):
    """A render changed which declared children are present."""


class SidewaysReadError(AttributeError):
    """A class body read a parameter off a sibling's declaration."""


##############################################
# Child declarations

class ChildDeclaration:
    """A node constructed in a class body: the class and the arguments,
    realized per parent instance.

    Not a data descriptor: after realization the parent's instance dict
    holds the real node under the same attribute, and that wins, so
    `_link_child`/`_attr_name_for` see exactly the tree they see today.
    Reading the attribute on the CLASS hands back the declaration, which
    is what `declared_children` and any later tooling want.
    """

    _name = None

    def __init__(self, node_class, args, kwargs):
        self.node_class = node_class
        self.args = tuple(args)
        self.kwargs = dict(kwargs)

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        raise AttributeError(
            f"child '{self._name}' of {type(instance).__name__} is not "
            f"realized on this instance")

    def __getattr__(self, attribute):
        if attribute.startswith('_'):
            raise AttributeError(attribute)
        held = f'{self._name}.{attribute}' if self._name else attribute
        raise SidewaysReadError(
            f"cannot read '{attribute}' off the {self.node_class.__name__} "
            f"declaration ({held}): a sibling's parameter is not a value in "
            f"a class body; declare the shared parameter on this class and "
            f"pass it to both children.")

    def repeat(self, count):
        """Count-many identical instances of this declaration."""
        return RepeatDeclaration(self, count)

    def realize(self, values, owner):
        args = [evaluate(arg, values) for arg in self.args]
        kwargs = {key: evaluate(arg, values)
                  for key, arg in self.kwargs.items()}
        return self.node_class(*args, **kwargs)

    def __repr__(self):
        return f'<declared {self.node_class.__name__} {self._name or ""}>'


class RepeatDeclaration:
    """`declaration.repeat(count)`: count-many identical children, one
    geometry with count placements."""

    _name = None

    def __init__(self, declaration, count):
        self.declaration = declaration
        self.count = count

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        raise AttributeError(
            f"children '{self._name}' of {type(instance).__name__} are not "
            f"realized on this instance")

    @property
    def node_class(self):
        return self.declaration.node_class

    def realize(self, values, owner):
        count = evaluate(self.count, values)
        if isinstance(count, float) and count.is_integer():
            count = int(count)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ParameterError(
                f"{owner}: repeat count for '{self._name}' must be a "
                f"non-negative integer, got {count!r}")
        return [self.declaration.realize(values, owner) for _ in range(count)]

    def __repr__(self):
        return (f'<declared {self.node_class.__name__} {self._name or ""} '
                f'x {self.count!r}>')


def _is_child_list(value):
    return (isinstance(value, list) and value
            and all(isinstance(item, ChildDeclaration) for item in value))


##############################################
# The metaclass and the class-body question

# The mark a node class body carries while it runs. CPython 3.12 inlines
# a comprehension into the body's frame (PEP 709) and, while the
# comprehension's hidden loop variable is live, `frame.f_locals` is a
# plain dict COPY of the namespace rather than the namespace itself; the
# copy still holds this entry, so the body is recognized in either form.
# The metaclass removes it before the class exists.
_BODY_KEY = '__solid_node_body__'
_BODY = object()


class _DeclaringNamespace(dict):
    """The namespace a node class body executes in.

    Its type -- or, during an inlined comprehension, the mark it
    carries -- is what a node constructor looks for on the stack, and
    its `__setitem__` names each declaration as it is assigned, so the
    rest of the body can talk about it by name.
    """

    def __init__(self):
        super().__init__()
        super().__setitem__(_BODY_KEY, _BODY)

    def __setitem__(self, key, value):
        if isinstance(value, (Declaration, ChildDeclaration,
                              RepeatDeclaration)):
            if isinstance(value, Declaration) and value._name is None:
                value._name = key
            elif not isinstance(value, Declaration):
                value._name = key
        super().__setitem__(key, value)


def in_class_body():
    """Whether a node class body is executing somewhere up the stack.

    The class statement runs its body as a frame whose locals are the
    namespace `NodeMeta.__prepare__` returned, so that namespace on the
    stack is the body, and a body that raised is not on the stack. Inside
    an inlined comprehension the frame reports a copy of the namespace
    instead (see `_BODY_KEY`); the copy carries the mark.
    """
    frame = sys._getframe(1)
    while frame is not None:
        found = frame.f_locals
        if (isinstance(found, _DeclaringNamespace)
                or (type(found) is dict and found.get(_BODY_KEY) is _BODY)):
            return True
        frame = frame.f_back
    return False


class NodeMeta(type):
    """The metaclass of every node class.

    It does two things and nothing else: hands the class statement the
    namespace that marks a body as executing (see `in_class_body`) and
    takes the mark back when the body is done, and names the
    declarations that body assigns. A project that gives a
    node its own metaclass derives it from this one, as `CheckCQEditor`
    does.
    """

    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        return _DeclaringNamespace()

    def __new__(mcs, name, bases, namespace, **kwargs):
        # The body has finished running: the mark has done its job and
        # is not an attribute of the class.
        namespace.pop(_BODY_KEY, None)
        return super().__new__(mcs, name, bases, namespace, **kwargs)


##############################################
# Enumeration

_children_cache = {}


def declared_children(node_class):
    """Every child declared on `node_class`, by attribute: a
    `ChildDeclaration`, a list of them, or a `RepeatDeclaration`."""
    cached = _children_cache.get(node_class)
    if cached is None:
        found = {}
        for klass in reversed(node_class.__mro__):
            for name, value in vars(klass).items():
                if isinstance(value, (ChildDeclaration, RepeatDeclaration)):
                    found[name] = value
                elif _is_child_list(value):
                    found[name] = list(value)
        cached = _children_cache[node_class] = found
    return cached


def is_declarative(node_class):
    """Whether the class declares anything: parameters or children."""
    return bool(declared_parameters(node_class)
                or declared_children(node_class))


##############################################
# Realization

def resolve_parameters(node_class, kwargs):
    """The resolved value of every declared and derived parameter of
    `node_class` for one instance, from the caller's keyword arguments
    and the declarations' defaults."""
    declared = declared_parameters(node_class)
    owner = node_class.__name__
    settable = [name for name, declaration in declared.items()
                if not declaration.derived]
    for name in kwargs:
        declaration = declared.get(name)
        if declaration is None:
            raise TypeError(
                f"{owner} has no parameter '{name}'; it declares: "
                f"{', '.join(settable) or 'none'}")
        if declaration.derived:
            raise TypeError(
                f"{owner}.{name} is derived from other parameters and cannot "
                f"be supplied; it declares: {', '.join(settable) or 'none'}")
    values = {}
    for name, declaration in declared.items():
        if declaration.derived:
            continue
        supplied = kwargs[name] if name in kwargs else declaration.default
        values[name] = declaration.resolve(supplied, owner)
    for name, declaration in declared.items():
        if declaration.derived:
            values[name] = declaration.evaluate(values)
    return values


def identity_values(node_class, values):
    """The declared (not derived) values, the part of `values` that
    identifies the instance's artifacts."""
    return {name: values[name]
            for name, declaration in declared_parameters(node_class).items()
            if not declaration.derived}


def realize_children(node):
    """Construct `node`'s declared children in declaration order, into
    its instance dict under the declaring attribute, named after it.

    The names are the ones `_link_child` would derive later; deriving
    them here as well means a child answers to its name from the moment
    it exists, and linking is idempotent so nothing changes when it runs.
    """
    values = node.__dict__.get('_parameters', {})
    owner = type(node).__name__
    for attribute, declaration in declared_children(type(node)).items():
        if isinstance(declaration, list):
            realized = [item.realize(values, owner) for item in declaration]
        else:
            realized = declaration.realize(values, owner)
        if isinstance(realized, list):
            for index, child in enumerate(realized):
                _name_child(child, f'{attribute}-{index}')
        else:
            _name_child(realized, attribute)
        node.__dict__[attribute] = realized


def _name_child(child, name):
    if not getattr(child, '_explicit_name', False):
        child.name = name


def declared_child_nodes(node):
    """The realized declared children of `node`, flattened in
    declaration order; empty for a class that declares none."""
    found = []
    for attribute in declared_children(type(node)):
        realized = node.__dict__.get(attribute)
        if realized is None:
            continue
        if isinstance(realized, list):
            found.extend(realized)
        else:
            found.append(realized)
    return found


def parse_overrides(node_class, pairs):
    """`--set name=value` words into keyword arguments for `node_class`,
    each parsed by the parameter's declared kind."""
    declared = declared_parameters(node_class)
    settable = [name for name, declaration in declared.items()
                if not declaration.derived]
    overrides = {}
    for pair in pairs or ():
        name, separator, text = pair.partition('=')
        if not separator or not name:
            raise ParameterError(
                f"cannot read {pair!r}: --set takes name=value")
        if not settable:
            raise ParameterError(
                f"{node_class.__name__} declares no parameters, so --set "
                f"{pair} has nothing to set")
        declaration = declared.get(name)
        if declaration is None:
            raise ParameterError(
                f"{node_class.__name__} has no parameter '{name}'; settable: "
                f"{', '.join(settable)}")
        if declaration.derived:
            raise ParameterError(
                f"{node_class.__name__}.{name} is derived from other "
                f"parameters and cannot be set; settable: "
                f"{', '.join(settable)}")
        overrides[name] = declaration.parse(text)
    return overrides
