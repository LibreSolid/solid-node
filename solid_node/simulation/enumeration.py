# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The one authority on what drivers a machine has, and what they are
called from outside it.

`declared_drivers(cls)` answers for a single class. That was enough
while a machine declared its drivers on the root, and stops being
enough the moment a machine is built out of mechanisms: a printer's
drivers live on its axes, and the root may declare none at all. Every
flat namespace that has to name a driver -- the simulation bank, an
instruction target, the serialized document's driver table, the
loader's opening snapshot -- therefore reads THIS walk, keyed by
qualified id (`solid_node.node.qualified`). One authority is the point:
the id in the document and the key in the bank are the same string
because they come from the same function, not because two
implementations agree.

The walk lives here, in the simulation layer, and freely imports the
node layer. The reverse never happens: `solid_node/node/` owns the
qualification MECHANISM (it must, to deliver a qualified `set_state`
entry) and knows nothing about drivers beyond the declaration marker.
"""

from solid_node.node.base import AbstractBaseNode
from solid_node.node.qualified import declared_drivers_of, drive_tree


def qualified_drivers(root):
    """Every driver declared in `root`'s tree, by qualified id.

    Binding is not a side effect to apologize for: finding the children
    means rendering, and a state-consuming assembly cannot be rendered
    under no snapshot at all, so the walk binds each declaration's own
    default as it descends. The framework still invents nothing -- the
    declarations state the values, and a caller with a real snapshot
    (a simulation tick, a serialization pass) binds over them
    immediately.
    """
    return drive_tree(
        root, lambda node, path, name, declaration: declaration.default)


def qualified_instructions(root):
    """Every instruction declared in `root`'s tree, by qualified name.

    `{qualified_name: (node, path, instruction)}`. An instruction is
    declared with class-local target names, so the declaring node's
    path is what turns `{'motor': 0.0}` into a target on
    `x_axis.motor`; a root-declared instruction keeps its bare name,
    exactly as a root-declared driver does.
    """
    found = {}

    def visit(node, path, _children):
        for name, instruction in getattr(node, 'instructions', {}).items():
            found['.'.join(path + (name,))] = (node, path, instruction)

    drive_tree(
        root, lambda node, path, name, declaration: declaration.default,
        visit)
    return found


def bind_declared_defaults(root):
    """Bind every declared default across `root`'s tree, and return the
    enumeration.

    This is what the build/test loader calls so a driver-declaring
    project builds, tests and serves without binding its own defaults
    in `__init__`. A tree that declares no driver is left strictly
    alone -- not walked, not rendered -- so a driverless project loads
    exactly as it did before this existed. The structural pre-check
    below answers that question without rendering anything, which is
    the only way to answer it without already being the behaviour
    change it is guarding against.
    """
    if not tree_declares_drivers(root):
        return {}
    return qualified_drivers(root)


def tree_declares_drivers(node, seen=None):
    """Whether anything in `node`'s constructed tree declares a driver.

    Structural, never rendering: it walks the node instances a parent
    already holds -- on its own attributes, in its lists and tuples,
    and in whatever a previous pass linked as `children`. That is the
    same place `_attr_name_for` derives names from, so it sees the tree
    a linked walk would see, minus children a render has yet to create.
    A false negative there costs a driver-declaring project the loud
    unbound-state error it would have had anyway; a false positive
    costs one extra walk. Neither can silently change a driverless
    project, which is what this guard is for.
    """
    if seen is None:
        seen = set()
    if id(node) in seen:
        return False
    seen.add(id(node))
    if declared_drivers_of(type(node)):
        return True
    for value in vars(node).values():
        if isinstance(value, AbstractBaseNode):
            candidates = (value,)
        elif isinstance(value, (list, tuple)):
            candidates = [item for item in value
                          if isinstance(item, AbstractBaseNode)]
        else:
            continue
        for child in candidates:
            if tree_declares_drivers(child, seen):
                return True
    return False
