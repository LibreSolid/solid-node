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

Beside it, the ``instructions`` table says what the machine can be TOLD to
do: each declared instruction's qualified name, its design-unit targets
keyed by qualified driver id, and its duration.  It is additive within
version 2 (ADR-056 stage 3b): an instruction targets a driver, so a
document carrying instructions necessarily carries a non-empty ``drivers``
table, which a consumer without driver evaluation already refuses loudly --
no consumer can misread the added key.  Both tables come from ONE walk:
``drive_tree`` visits every assembly after binding its drivers, so the
instruction declarations are collected in the same descent that builds the
symbolic expressions.

Version 3 adds the ``flexible`` node shape: a part whose GEOMETRY follows
the machine travels as its shape spec plus one expression per parameter,
never as a mesh, so the consumer evaluates shape the way it already
evaluates pose.  The version is a property of the CONTENT, not of the
producer -- ``document_version`` reads it off the finished tree -- because
a document holding no flexible node is byte-identical to the version 2 it
has always been, and claiming otherwise would make an old consumer refuse
documents it renders perfectly.
"""

from contextlib import contextmanager

from solid_node.node.qualified import (
    DriverToken, declared_drivers_of, driver_id, drive_tree,
)
from solid_node.simulation.enumeration import tree_declares_drivers


DOCUMENT_FORMAT = 'solid-node-export'

#: The version a document without flexible content declares -- which is
#: every document the producer emitted before flexible parts existed, and
#: byte-for-byte the same one.
DOCUMENT_VERSION = 2

#: The version a document carrying at least one flexible node declares.
#: A new tree shape is a breaking change (ADR-034), so it needs a bump;
#: emitting it only where the content needs it is the drivers-table
#: precedent, and it is what keeps an old consumer refusing exactly the
#: documents it genuinely cannot render.
FLEXIBLE_DOCUMENT_VERSION = 3


@contextmanager
def symbolic_drivers(node):
    """Serialize ``node`` in symbolic driver mode, then restore it.

    Yields ``{qualified_id: declaration}`` for every driver in the tree.
    The instruction half of the same walk is available through
    ``symbolic_document``; this name stays for a caller that only wants
    the drivers.
    """
    with symbolic_document(node) as (declarations, _):
        yield declarations


@contextmanager
def symbolic_document(node):
    """Serialize ``node`` in symbolic driver mode, then restore it.

    Yields ``(declarations, instructions)``: ``{qualified_id:
    declaration}`` for every driver in the tree, with each one bound to a
    token whose string is its own id, so ordinary solid2 arithmetic has
    already produced the wire expression by the time the walk renders; and
    ``{qualified_name: (path, instruction)}`` for every instruction the
    same descent found.  The mode binds ALL the drivers -- never a subset,
    so no render can find a hole -- and afterwards restores exactly the
    snapshot each node held and re-renders under it, so a caller that had a
    numeric pose still has one.

    A tree that declares no drivers is not walked at all: it has nothing to
    bind, and a walk would render it for no reason.  Its document is the
    version 1 document with two empty tables added -- including the
    instruction one, because an instruction moves a driver and a tree with
    no drivers has nothing for one to move.
    """
    if not tree_declares_drivers(node):
        yield {}, {}
        return

    previous = {}
    instructions = {}

    def symbolic(target, path, name, declaration):
        if id(target) not in previous:
            previous[id(target)] = (target, dict(target._states))
        return DriverToken(driver_id(path, name))

    def collect(target, path):
        for name, instruction in getattr(target, 'instructions', {}).items():
            instructions['.'.join(path + (name,))] = (path, instruction)

    declarations = drive_tree(node, symbolic, collect)
    try:
        yield declarations, instructions
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
    or the viewer clamps to it -- and is carried in the DESIGN units it
    was declared in, beside a ``default`` that is native.  The producer
    deliberately does not convert it: a client that received one reading
    of a scaled driver's bounds could not tell which one it was, while a
    client holding both the range and the ``scale`` converts once, exactly
    as ``Driver.native`` converts an instruction target.
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


def instructions_table(instructions):
    """The document's ``instructions`` table: what the machine can be told.

    ``instructions`` is what ``symbolic_document`` collected --
    ``{qualified_name: (declaring path, instruction)}``.  A declaration
    names its targets class-locally (``{'motor': 0.0}``), so the declaring
    node's path is what turns them into targets on ``x_axis.motor``: the
    same qualification, through the same ``driver_id``, that keyed the
    driver table, so a client resolves a target against a declared driver
    by string equality rather than by two schemes agreeing.

    Targets stay in DESIGN units, verbatim, and the duration in seconds.
    The conversion to native state belongs to the driver declaration --
    the one place that knows what a native unit is worth -- and happens
    once, in the client, exactly as ``Driver.native`` performs it.
    """
    return {
        name: {
            'targets': {driver_id(path, target): value
                        for target, value in instruction.targets.items()},
            'duration': instruction.duration,
        }
        for name, (path, instruction) in sorted(instructions.items())
    }


def document_version(root):
    """The LOWEST schema version the serialized tree ``root`` needs.

    Read off the document rather than tracked while building it, so the
    three producers that share this walk cannot disagree about what they
    just emitted.  A tree carrying a flexible node carries a shape no
    version 2 consumer knows and says so; a tree carrying none is
    unchanged in every byte and claims nothing new, which is what lets a
    consumer that cannot render flexible parts keep rendering every
    document that has none -- and refuse loudly only on one that has
    them, rather than render nothing where a spring belongs.
    """
    if 'flexible' in root:
        return FLEXIBLE_DOCUMENT_VERSION
    for child in root.get('children', ()):
        if document_version(child) != DOCUMENT_VERSION:
            return FLEXIBLE_DOCUMENT_VERSION
    return DOCUMENT_VERSION


def serialize_node(node, model_path, piece_id=None):
    """Serialize one node using ``model_path`` for rigid artifacts.

    The established parent-linking rule must run before recursion because a
    render may create and bind a fresh child on each invocation.  A rigid node
    is a terminal model reference; a flexible leaf is a terminal ``flexible``
    object carrying the spec its geometry travels as; a non-list/tuple
    non-rigid render keeps the existing partial-node representation for
    lifecycle validation to handle.

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

    if node.flexible:
        # No model reference and no piece: its geometry is the spec, and
        # a part that deforms is no printed solid.  The recursion stops
        # here for the same reason it stops at a rigid node -- a leaf.
        data['flexible'] = node.flexible_document()
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
