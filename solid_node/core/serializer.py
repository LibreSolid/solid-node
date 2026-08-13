# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The common versioned node-tree document serializer.

Export and published build snapshots have one observable node schema while
their rigid-model paths remain producer-owned: export maps models into a
portable copied ``models/`` tree, whereas a build maps them relative to its
published root.  Keeping that difference in a supplied mapper makes the tree
walk itself one source of truth without making builds portable by accident.
"""


DOCUMENT_FORMAT = 'solid-node-export'
DOCUMENT_VERSION = 1


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
