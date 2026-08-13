# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Content-derived printed-piece identity (printed-pieces capability).

A piece is the answer to "is this the same thing to print?" -- a
question about the built artifact's content, never about the node class,
its constructor parameters, or its tree position. ``uniq_id`` (ADR-026)
answers a different question (the build-cache key) and is untouched here.

``PieceInventory`` is the accumulator every producer (builder, exporter,
browser snapshot renderer) shares: one instance per publication, fed
through the ``piece_id`` mapper ``serialize_node`` calls for every rigid
node in document order, so first-encounter order falls out of the walk
itself.
"""

import hashlib
import logging
import os

from solid_node.node.base import cached_base_mesh

logger = logging.getLogger('core.pieces')

# Hex digits of the sha256 kept in a piece id -- the same bound
# node/base.py uses for the artifact key, for the same reason: short
# enough to stay out of the way, long enough that accidental collisions
# are not a practical concern for a single project's build tree.
_HASH_LEN = 12

# Module-level cache of artifact content fingerprints, keyed on
# (path, mtime) -- the same shape as node/base.py's base-mesh cache, so a
# rebuilt STL is picked up and a stale entry under its old mtime is
# evicted rather than accumulating one per rebuild.
_fingerprint_cache = {}


def fingerprint_artifact(path):
    """The content identity of a built artifact: sha256 of its bytes,
    truncated to _HASH_LEN hex digits. Cached per (path, mtime): a
    project's already-loaded mesh cache does not need a second read of
    the same file, and this cache does not need one either across a
    republication that finds every artifact still current."""
    mtime = os.path.getmtime(path)
    key = (path, mtime)
    cached = _fingerprint_cache.get(key)
    if cached is None:
        for stale in [k for k in _fingerprint_cache if k[0] == path]:
            del _fingerprint_cache[stale]
        with open(path, 'rb') as artifact:
            cached = hashlib.sha256(artifact.read()).hexdigest()[:_HASH_LEN]
        _fingerprint_cache[key] = cached
    return cached


def _geometry_facts(path):
    """size/volume/watertight read from the artifact's own base mesh --
    never node.mesh, which applies world placement and $t and would leak
    pose into facts that are supposed to be placement-independent.

    Tolerates an unloadable or unclosed mesh instead of raising: a piece
    whose facts cannot be derived is still published (design.md
    'Failure is reported, not fatal'), with watertight false and no
    size/volume rather than aborting the whole document."""
    try:
        mesh = cached_base_mesh(path)
        size = [float(value) for value in mesh.extents]
        volume = float(mesh.volume)
        watertight = bool(mesh.is_watertight)
        return size, volume, watertight
    except Exception:
        logger.warning('Could not derive geometry facts for %s', path,
                       exc_info=True)
        return None, None, False


def _project_relative_source(node):
    """node.src, relative to its project root, so the inventory names a
    source the way a maker reading the project would recognise it rather
    than an absolute filesystem path.

    Falls back to whatever identifies the node when a project root cannot
    be discovered, and to its artifact path when the node carries no
    ``src`` at all (a minimal test double standing in for a real node) --
    a piece is still published rather than the whole registration failing
    (design.md 'Failure is reported, not fatal').
    """
    from solid_node.core.loader import project_root, ProjectManifestError

    src = getattr(node, 'src', None)
    if src is None:
        return getattr(node, 'stl_file', repr(node))
    try:
        root = project_root(src)
        return os.path.relpath(src, root)
    except (ProjectManifestError, OSError):
        return src


class PieceInventory:
    """Accumulates the printed-piece inventory during one tree walk.

    One instance per publication. ``register`` is the ``piece_id``
    mapper ``serialize_node`` calls for every rigid node; the producer
    reads the accumulated ``pieces()`` list back out once the walk is
    complete.
    """

    def __init__(self):
        self._order = []
        self._pieces = {}

    def register(self, node, model):
        """Resolve `node`'s piece id, folding it into the inventory.

        `model` is the ALREADY-RESOLVED reference the producer just
        wrote into the document (build-root-relative or
        models/-relative), so each producer records exactly the
        reference it publishes -- no second mapping happens here.
        """
        # An unreadable artifact is not fingerprinted from something
        # else: identity is content or it is nothing. There is no
        # fallback to uniq_id here, because uniq_id is exactly the
        # class-and-parameters key this capability exists to stop
        # standing in for geometry. Publication is already gated on
        # every artifact being current, so an artifact that cannot be
        # read is an internal inconsistency and the OSError belongs to
        # whoever published a tree naming it.
        piece_id = fingerprint_artifact(node.stl_file)
        size, volume, watertight = _geometry_facts(node.stl_file)

        source = _project_relative_source(node)
        entry = self._pieces.get(piece_id)
        if entry is None:
            entry = {
                'id': piece_id,
                'name': node.__class__.__name__,
                'sources': set(),
                'models': set(),
                'count': 0,
                'size': size,
                'volume': volume,
                'watertight': watertight,
            }
            self._pieces[piece_id] = entry
            self._order.append(piece_id)
        entry['sources'].add(source)
        entry['models'].add(model)
        entry['count'] += 1
        return piece_id

    def pieces(self):
        """The inventory as a list, ordered by first encounter, with
        contributor sets rendered as sorted lists so nothing about a
        merge is order-dependent."""
        return [
            {
                **self._pieces[piece_id],
                'sources': sorted(self._pieces[piece_id]['sources']),
                'models': sorted(self._pieces[piece_id]['models']),
            }
            for piece_id in self._order
        ]
