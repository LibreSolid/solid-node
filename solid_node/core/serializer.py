# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The common versioned node-tree document serializer.

Export and published build snapshots have one observable node schema while
their rigid-model paths remain producer-owned: export maps models into a
portable copied ``models/`` tree, whereas a build maps them relative to its
published root.  Keeping that difference in a supplied mapper makes the tree
walk itself one source of truth without making builds portable by accident.

Version 2 adds named drivers.  An operation records whatever value
``render()`` computed, so a document serialized from a numerically stepped
node would publish the constants of one instant -- exactly the defect ``$t``
already had, and which export already answers by returning the node to
symbolic animation time before serializing.  ``symbolic_drivers`` extends
that same producer obligation to drivers: bind every declared driver of the
tree to its qualified token, serialize, restore.  It is a distinct internal
path and never ``set_state``, whose numbers-only contract is what keeps a
bound pose a pure function of numbers.

The accompanying ``drivers`` table publishes each qualified id's declared
metadata, so a consumer can present the inputs an expression names.  It is
presentation metadata: ``range`` in particular is never a clamp.  A tree
declaring no drivers serializes an empty table and is byte-for-byte the
document version 1 published, which is what lets a consumer that cannot yet
evaluate driver expressions keep rendering every document that has none --
and fail loudly on one that has them, rather than render a wrong pose.
"""

from contextlib import contextmanager

from solid_node.node.qualified import (
    DriverToken, declared_drivers_of, driver_id, drive_tree,
)
from solid_node.simulation.enumeration import tree_declares_drivers


DOCUMENT_FORMAT = 'solid-node-export'
DOCUMENT_VERSION = 2


@contextmanager
def symbolic_drivers(node):
    """Serialize ``node`` in symbolic driver mode, then restore it.

    Yields ``{qualified_id: declaration}`` for every driver in the tree,
    with each one bound to a token whose string is its own id, so ordinary
    solid2 arithmetic has already produced the wire expression by the time
    the walk renders.  The mode binds ALL of them -- never a subset, so no
    render can find a hole -- and afterwards restores exactly the snapshot
    each node held and re-renders under it, so a caller that had a numeric
    pose still has one.

    A tree that declares no drivers is not walked at all: it has nothing to
    bind, and a walk would render it for no reason.  Its document is the
    version 1 document with an empty table added.
    """
    if not tree_declares_drivers(node):
        yield {}
        return

    previous = {}

    def symbolic(target, path, name, declaration):
        if id(target) not in previous:
            previous[id(target)] = (target, dict(target._states))
        return DriverToken(driver_id(path, name))

    declarations = drive_tree(node, symbolic)
    try:
        yield declarations
    finally:
        for target, states in previous.values():
            target._states.clear()
            target._states.update(states)
        # Re-render under the restored snapshot: an operation holds the
        # value its render computed, so nothing else would drop the tokens.
        # Unless the prior binding had holes -- a tree nobody bound could
        # not be rendered before this either, and inventing a value to
        # re-render it with is exactly what the unbound contract forbids.
        # Its stale operations are swept by whatever renders it next.
        if all(name in states
               for target, states in previous.values()
               for name in declared_drivers_of(type(target))):
            drive_tree(node, lambda target, path, name, declaration:
                       target._states[name])


def drivers_table(declarations):
    """The document's ``drivers`` table: each qualified id's declaration.

    ``dtype`` is published by name because a document is JSON and a Python
    type is not; everything else travels verbatim.  A declaration's
    ``range`` is carried for presentation only -- nothing in the framework
    or the viewer clamps to it.
    """
    return {
        identifier: {
            'default': declaration.default,
            'range': (list(declaration.range)
                      if declaration.range is not None else None),
            'unit': declaration.unit,
            'dtype': (declaration.dtype.__name__
                      if declaration.dtype is not None else None),
            'scale': declaration.scale,
        }
        for identifier, declaration in sorted(declarations.items())
    }


def serialize_node(node, model_path, piece_id=None):
    """Serialize one node using ``model_path`` for rigid artifacts.

    The established parent-linking rule must run before recursion because a
    render may create and bind a fresh child on each invocation.  A rigid node
    is a terminal model reference; a non-list/tuple non-rigid render keeps the
    existing partial-node representation for lifecycle validation to handle.

    ``piece_id``, when supplied, is called as ``piece_id(node, model)`` for
    every rigid node -- ``model`` being the reference just resolved above --
    and its return value is published as ``piece``. It defaults to ``None``
    so every existing caller keeps its previous, piece-free document.
    """
    data = {
        'name': node.name,
        'type': node._type,
        'color': node.color,
        'mtime': node.mtime,
        'operations': [operation.serialized for operation in node.operations],
    }
    if node.rigid:
        model = model_path(node)
        data['model'] = model
        if piece_id is not None:
            data['piece'] = piece_id(node, model)
        return data

    children = node.render()
    if type(children) not in (list, tuple):
        return data

    for child in children:
        node._link_child(child)
    data['children'] = [
        serialize_node(child, model_path, piece_id) for child in children
    ]
    return data
