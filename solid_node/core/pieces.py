# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Content-derived printed-piece identity (printed-pieces capability)."""

import hashlib
import io
import json
import logging
import math
import os
import tempfile

from solid_node._artifact import ArtifactSnapshot


logger = logging.getLogger('core.pieces')

_HASH_LEN = 12
_FACT_VERSION = 1
_FACT_SUFFIX = '.piece-facts.json'


class PieceIdCollisionError(RuntimeError):
    """Distinct complete artifact digests share one public piece id."""

    def __init__(self, piece_id, digests):
        first, second = sorted(digests)
        super().__init__(
            f'Printed-piece id collision for {piece_id!r}: distinct '
            f'SHA-256 digests {first} and {second}')


def fact_sidecar(artifact):
    """The private persistent fact record beside ``artifact``."""
    return f'{artifact}{_FACT_SUFFIX}'


def describes(path):
    """Return the artifact path described by a fact sidecar, if any."""
    if path.endswith(_FACT_SUFFIX):
        return path[:-len(_FACT_SUFFIX)]
    return None


def _atomic_write(path, content):
    directory = os.path.dirname(os.path.abspath(path)) or '.'
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f'.{os.path.basename(path)}.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(content)
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


def _geometry_facts_from_bytes(path, data):
    """Derive tolerant geometry facts from the same bytes as the digest."""
    try:
        # Import only on the mesh-reading path. Merely importing nodes, the
        # CLI, or this inventory must retain the established lazy dependency.
        import trimesh
        mesh = trimesh.load(io.BytesIO(data), file_type='stl')
        size = [float(value) for value in mesh.extents]
        volume = float(mesh.volume)
        watertight = bool(mesh.is_watertight)
        if (len(size) != 3 or any(not math.isfinite(value) or value < 0
                                  for value in size)
                or not math.isfinite(volume)):
            raise ValueError('mesh facts are not finite printable values')
        return size, volume, watertight
    except Exception:
        logger.warning('Could not derive geometry facts for %s', path,
                       exc_info=True)
        return None, None, False


def _geometry_facts(path):
    """Compatibility seam: facts from one coherent, uncached artifact read."""
    with ArtifactSnapshot(path) as snapshot:
        return _geometry_facts_from_bytes(path, snapshot.read_bytes())


def _digest_bytes(data):
    """Patchable counter seam for full artifact hashing."""
    return hashlib.sha256(data).hexdigest()


def fingerprint_artifact(path):
    """The compatible public content id from one coherent artifact read."""
    with ArtifactSnapshot(path) as snapshot:
        return _digest_bytes(snapshot.read_bytes())[:_HASH_LEN]


def _valid_number(value):
    return (isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value))


def _read_fact_record(path, observation):
    """Read one strict known-version record, or certify nothing."""
    try:
        with open(fact_sidecar(path), encoding='utf-8') as source:
            record = json.load(source)
        if not isinstance(record, dict) or set(record) != {
                'version', 'artifact', 'sha256', 'size', 'volume',
                'watertight'}:
            return None
        if (not isinstance(record['version'], int)
                or isinstance(record['version'], bool)
                or record['version'] != _FACT_VERSION):
            return None
        from solid_node._artifact import ArtifactObservation
        if ArtifactObservation.from_record(record['artifact']) != observation:
            return None
        digest = record['sha256']
        if (not isinstance(digest, str) or len(digest) != 64
                or any(char not in '0123456789abcdef' for char in digest)):
            return None
        size, volume, watertight = (
            record['size'], record['volume'], record['watertight'])
        if not isinstance(watertight, bool):
            return None
        if size is None or volume is None:
            if size is not None or volume is not None or watertight:
                return None
        elif (not isinstance(size, list) or len(size) != 3
              or not all(_valid_number(value) and value >= 0 for value in size)
              or not _valid_number(volume)):
            return None
        return digest, size, volume, watertight
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _publish_fact_record(path, observation, facts):
    digest, size, volume, watertight = facts
    record = {
        'version': _FACT_VERSION,
        'artifact': observation.record(),
        'sha256': digest,
        'size': size,
        'volume': volume,
        'watertight': watertight,
    }
    _atomic_write(
        fact_sidecar(path),
        json.dumps(record, sort_keys=True, separators=(',', ':')).encode())


def _project_relative_source(node):
    from solid_node.core.loader import project_root, ProjectManifestError

    src = getattr(node, 'src', None)
    if src is None:
        return getattr(node, 'stl_file', repr(node))
    try:
        root = project_root(src)
        return os.path.relpath(src, root)
    except (ProjectManifestError, OSError):
        return src


def _source_current(node, artifact, read_only=False):
    """Whether this node's settled currency contract vouches for the STL."""
    if read_only:
        # Browser staging is a pure reader. `_up_to_date` may restamp an
        # equal-content artifact and rewrite its currency sidecar on the
        # fallback path, so only its settled metadata-only branch is safe.
        try:
            if os.stat(artifact).st_mtime_ns != node.mtime_ns:
                return False
            fingerprint = node.source_fingerprint
            from solid_node import currency
            return (fingerprint is not None
                    and currency.recorded_fingerprint(artifact) == fingerprint)
        except (AttributeError, OSError, ValueError):
            return False
    current = getattr(node, '_up_to_date', None)
    if current is None:
        return False
    try:
        return bool(current(artifact))
    except (OSError, ValueError):
        return False


class PieceInventory:
    """One publication's live metadata plus pinned artifact facts."""

    def __init__(self, publish_facts=True):
        self.publish_facts = publish_facts
        self._order = []
        self._pieces = {}
        self._full_digests = {}
        self._snapshots = {}
        self._facts = {}

    def _artifact_facts(self, node):
        path = os.path.abspath(os.fspath(node.stl_file))
        cached = self._facts.get(path)
        if cached is not None:
            return cached

        # Currency can legitimately restamp an equal-content artifact. Do it
        # before opening the identity whose ctime must remain stable.
        current = _source_current(
            node, path, read_only=not self.publish_facts)
        snapshot = ArtifactSnapshot(path)
        try:
            facts = (_read_fact_record(path, snapshot.observation)
                     if current else None)
            if facts is None:
                data = snapshot.read_bytes()
                digest = _digest_bytes(data)
                size, volume, watertight = _geometry_facts_from_bytes(
                    path, data)
                facts = digest, size, volume, watertight
                if self.publish_facts:
                    try:
                        _publish_fact_record(
                            path, snapshot.observation, facts)
                    except OSError as error:
                        # Facts remain correct in this live publication. A
                        # missing record merely makes the next one recompute.
                        logger.debug(
                            'Could not persist piece facts for %s: %s',
                            path, error)
                    snapshot.validate()
            self._snapshots[path] = snapshot
            self._facts[path] = facts
            return facts
        except Exception:
            snapshot.close()
            raise

    def register(self, node, model):
        """Resolve ``node`` and fold current model metadata into the walk."""
        full_digest, size, volume, watertight = self._artifact_facts(node)
        piece_id = full_digest[:_HASH_LEN]
        existing_digest = self._full_digests.get(piece_id)
        if existing_digest is not None and existing_digest != full_digest:
            raise PieceIdCollisionError(
                piece_id, (existing_digest, full_digest))
        self._full_digests[piece_id] = full_digest

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

    def copy_artifact(self, path, target):
        """Copy bytes from the identity already used for this inventory."""
        snapshot = self._snapshots[os.path.abspath(os.fspath(path))]
        snapshot.copy_to(target)

    def validate(self):
        """Revalidate every pinned artifact immediately before publication."""
        for snapshot in self._snapshots.values():
            snapshot.validate()

    def pieces(self):
        return [
            {
                **self._pieces[piece_id],
                'sources': sorted(self._pieces[piece_id]['sources']),
                'models': sorted(self._pieces[piece_id]['models']),
            }
            for piece_id in self._order
        ]

    def close(self):
        snapshots, self._snapshots = self._snapshots, {}
        for snapshot in snapshots.values():
            snapshot.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
