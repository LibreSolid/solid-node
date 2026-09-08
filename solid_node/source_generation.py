# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Process-local identity for the project source one builder executes.

Artifact currency answers whether files on disk still describe an artifact.
This module answers the earlier question: whether live project classes and an
artifact-producing phase still describe the files they actually read.  The
answer is deliberately short-lived.  A generation belongs to one request in
one interpreter, and every phase takes a new census.
"""

import contextvars
import hashlib
import importlib.abc
import importlib.machinery
import os
import sys
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass


class SourceChanged(RuntimeError):
    """The live project or producing phase no longer matches disk source."""


@dataclass(frozen=True)
class SourceObservation:
    """The observable identity ADR-081 assigns to one source path."""

    path: str
    device: int
    inode: int
    size: int
    mtime_ns: int
    ctime_ns: int

    @property
    def metadata(self):
        return (self.device, self.inode, self.size,
                self.mtime_ns, self.ctime_ns)


@dataclass(frozen=True)
class _PendingScadPublication:
    """One immutable desired path state captured during assembly."""

    path: str
    content: str
    mtime_ns: int
    digest: str | None
    fingerprint: str | None
    publish: object


def _observation(path, stat):
    return SourceObservation(
        path, stat.st_dev, stat.st_ino, stat.st_size,
        stat.st_mtime_ns, stat.st_ctime_ns)


def _observe_real_path(real):
    """Observe an already canonical path without resolving it again."""
    return _observation(real, os.stat(real))


def _observe_path(path):
    """Take one uncached path observation.  Patchable for cost/race tests."""
    real = os.path.realpath(path)
    return _observe_real_path(real)


def _changed(label, path, expected=None, actual=None):
    detail = ''
    if expected is not None or actual is not None:
        detail = f' (expected {expected!r}, found {actual!r})'
    return SourceChanged(
        f"Project source changed at {label}: {os.path.realpath(path)}{detail}")


def _coherent_real_source_bytes(real, verify_path=True):
    """Read bytes tied to one stable canonical path and open identity.

    Python's timestamp pyc check is intentionally absent.  Project modules are
    compiled from these bytes, and callers perform another uncached observation
    after execution so replacement between this read and live classes cannot be
    certified.
    """
    with open(real, 'rb') as source:
        opened_before = _observation(real, os.fstat(source.fileno()))
        data = source.read()
        opened_after = _observation(real, os.fstat(source.fileno()))
    path_after = opened_after
    if verify_path:
        try:
            path_after = _observe_real_path(real)
        except OSError:
            raise _changed('source read', real, opened_before, None) from None
    if opened_before != opened_after or opened_before != path_after:
        raise _changed('source read', real, opened_before, path_after)
    return data, opened_before


def _coherent_source_bytes(path):
    """Resolve and coherently read project source.  Patchable by race tests."""
    spelling = os.path.abspath(os.fspath(path))
    real = os.path.realpath(spelling)
    data, observation = _coherent_real_source_bytes(real)
    actual_real = os.path.realpath(spelling)
    if actual_real != real:
        raise _changed('source read path', spelling, real, actual_real)
    return data, observation


def _coherent_real_source_digest(real):
    """Hash an already canonical file without retaining its payload."""
    with open(real, 'rb') as source:
        opened_before = _observation(real, os.fstat(source.fileno()))
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
        opened_after = _observation(real, os.fstat(source.fileno()))
    if opened_before != opened_after:
        raise _changed('source digest', real, opened_before, opened_after)
    return digest, opened_before


class SourceCensus:
    """One phase's distinct-path observations and content memo.

    An entry is written once and never replaced.  New contributors may join
    before they are consumed (nested node producers do this), but observing an
    already-known path always returns the original frozen observation.  A
    boundary check constructs fresh observations rather than refreshing this
    object in place.
    """

    def __init__(self, root):
        root_spelling = os.path.abspath(os.fspath(root))
        self.root = os.path.realpath(root_spelling)
        self._observations = {}
        # Per-census only: repeated node closures use the same spellings, and
        # realpath itself performs filesystem work.  A boundary deliberately
        # does not reuse this map; it resolves every spelling afresh.
        self._canonical = {root_spelling: self.root}
        self._spellings = {root_spelling: self.root}
        self._spelling_order = [root_spelling]
        self._observation_order = []
        self._bytes = {}
        self._digests = {}
        self._sealed = False

    @property
    def paths(self):
        return frozenset(self._observations)

    def __contains__(self, path):
        return self._canonical_path(path) in self._observations

    def _canonical_path(self, path):
        spelling = os.path.abspath(os.fspath(path))
        real = self._canonical.get(spelling)
        if real is None:
            real = os.path.realpath(spelling)
            self._canonical[spelling] = real
            self._spellings[spelling] = real
            self._spelling_order.append(spelling)
        return real

    def __getitem__(self, path):
        real = self._canonical_path(path)
        if real not in self._observations:
            self.include((real,))
        return self._observations[real]

    def realpath(self, path):
        """Canonicalize one spelling once for this census."""
        return self._canonical_path(path)

    def include(self, paths):
        """Observe every previously unseen canonical path exactly once."""
        for path in paths:
            real = self._canonical_path(path)
            if real in self._observations:
                continue
            if self._sealed:
                raise SourceChanged(
                    f'Project source appeared after census sealed: {real}')
            self._observations[real] = _observe_real_path(real)
            self._observation_order.append(real)
        return self

    def adopt(self, observation):
        """Include a pre-execution/coherent-read observation without restat."""
        existing = self._observations.get(observation.path)
        if existing is not None and existing != observation:
            raise _changed('census incorporation', observation.path,
                           existing, observation)
        if existing is None:
            if self._sealed:
                raise SourceChanged(
                    f'Project source appeared after census sealed: '
                    f'{observation.path}')
            self._observations[observation.path] = observation
            self._observation_order.append(observation.path)
            if observation.path not in self._canonical:
                self._spelling_order.append(observation.path)
            self._canonical[observation.path] = observation.path
            self._spellings[observation.path] = observation.path

    def seal(self):
        self._sealed = True
        return self

    def read_bytes(self, path):
        """Read once, requiring the bytes to have this census's identity."""
        observation = self[path]
        cached = self._bytes.get(observation.path)
        if cached is not None:
            return cached
        try:
            data, actual = _coherent_real_source_bytes(
                observation.path, verify_path=False)
        except OSError:
            raise _changed('source content', observation.path,
                           observation, None) from None
        if actual != observation:
            raise _changed('source content', observation.path,
                           observation, actual)
        self._bytes[observation.path] = data
        return data

    def digest(self, path):
        observation = self[path]
        cached = self._digests.get(observation.path)
        if cached is None:
            data = self._bytes.get(observation.path)
            if data is not None:
                cached = hashlib.sha256(data).hexdigest()
            else:
                cached, actual = _coherent_real_source_digest(
                    observation.path)
                if actual != observation:
                    raise _changed('source content', observation.path,
                                   observation, actual)
            self._digests[observation.path] = cached
        return cached

    def fingerprint(self, files, root=None):
        root = self._canonical_path(root or self.root)
        entries = {}
        for path in files:
            observation = self[path]
            entries[os.path.relpath(observation.path, root)] = \
                observation.metadata
        fingerprint = hashlib.sha256()
        for relative, metadata in sorted(entries.items()):
            fingerprint.update(os.fsencode(relative))
            fingerprint.update(b'\0')
            fingerprint.update(','.join(map(str, metadata)).encode('ascii'))
            fingerprint.update(b'\n')
        return fingerprint.hexdigest()

    def check_current(self, paths=(), label='phase boundary'):
        """Compare a wholly fresh distinct-path census with this one."""
        requested = {self._canonical_path(path) for path in paths}
        missing = requested - self.paths
        if missing:
            raise SourceChanged(
                f"Project source appeared at {label}: {sorted(missing)[0]}")
        # Resolve original spellings without the census memo.  A symlink or
        # alias retarget is a source-set change even when the old target still
        # exists unchanged.
        for spelling, expected_real in self._spellings.items():
            actual_real = os.path.realpath(spelling)
            if actual_real != expected_real:
                raise SourceChanged(
                    f'Project source path changed at {label}: {spelling} '
                    f'(expected {expected_real}, found {actual_real})')
        for path, expected in self._observations.items():
            try:
                actual = _observe_real_path(path)
            except OSError:
                raise _changed(label, path, expected, None) from None
            if actual != expected:
                raise _changed(label, path, expected, actual)
        return True


_current_generation = contextvars.ContextVar(
    'solid_node_source_generation', default=None)
_current_phase = contextvars.ContextVar('solid_node_source_phase', default=None)


def current_generation():
    return _current_generation.get()


def current_phase():
    return _current_phase.get()


def current_census():
    phase = current_phase()
    return phase.census if phase is not None else None


class _ProjectSourceLoader(importlib.abc.Loader):

    def __init__(self, generation, wrapped, path):
        self.generation = generation
        self.wrapped = wrapped
        self.path = os.path.realpath(path)

    def create_module(self, spec):
        create = getattr(self.wrapped, 'create_module', None)
        return create(spec) if create is not None else None

    def exec_module(self, module):
        data, observation = _coherent_source_bytes(self.path)
        self.generation._before_import(module.__name__, observation)
        code = compile(data, self.path, 'exec', dont_inherit=True)
        exec(code, module.__dict__)
        self.generation._after_import(module.__name__, observation)


class _ProjectSourceFinder(importlib.abc.MetaPathFinder):

    def __init__(self, generation):
        self.generation = generation

    def find_spec(self, fullname, path=None, target=None):
        if path is not None and not any(
                self.generation.contains(entry) for entry in path):
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None or not spec.origin or not spec.origin.endswith('.py'):
            return None
        origin = os.path.realpath(spec.origin)
        if not self.generation.contains(origin):
            # Another custom finder (pytest assertion rewriting, tracing,
            # import instrumentation) must still get its ordinary chance for
            # external modules.  This finder claims project source only.
            return None
        if not isinstance(spec.loader, _ProjectSourceLoader):
            spec.loader = _ProjectSourceLoader(
                self.generation, spec.loader, origin)
        return spec


class SourcePhase:

    def __init__(self, generation, paths, label):
        self.generation = generation
        self.initial_paths = tuple(paths)
        self.label = label
        self.census = SourceCensus(generation.root)
        # Only the Builder's assembly producer owns the lifetime needed to
        # delay non-rigid SCAD publication safely. Other source phases retain
        # their existing immediate behavior.
        self.coalesces_scad = label == 'assembly'
        self._pending_scad = OrderedDict()
        self._token = None

    def __enter__(self):
        if current_phase() is not None:
            raise RuntimeError('A source phase cannot be nested')
        self._token = _current_phase.set(self)
        try:
            self.include(self.initial_paths)
            self._merge_generation_sources(fresh=True)
        except BaseException:
            self.census.seal()
            _current_phase.reset(self._token)
            self._token = None
            raise
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None:
                if self.coalesces_scad:
                    self.checkpoint(label=f'{self.label} pre-flush')
                    self._flush_scad()
                    self.checkpoint(label=f'{self.label} post-flush')
                else:
                    self.checkpoint(label=f'{self.label} post')
        finally:
            # Body/pre-flush failure discards every desired state. A flush
            # failure may leave already completed atomic publications, but no
            # later queued path is attempted and no request survives the
            # phase.
            self._pending_scad.clear()
            self.census.seal()
            _current_phase.reset(self._token)

    @property
    def pending_scad_count(self):
        return len(self._pending_scad)

    def defer_scad(self, path, content, mtime_ns, digest, fingerprint,
                   publish):
        """Retain the last immutable desired state for a canonical path."""
        if not self.coalesces_scad:
            raise RuntimeError('SCAD publication requires an assembly phase')
        canonical = os.path.realpath(path)
        # Re-insertion moves the path to its last occurrence relative to all
        # other paths, preserving the order the immediate implementation left
        # observable when a later publication fails.
        self._pending_scad.pop(canonical, None)
        self._pending_scad[canonical] = _PendingScadPublication(
            os.fspath(path), content, mtime_ns, digest, fingerprint, publish)

    def _flush_scad(self):
        pending = tuple(self._pending_scad.values())
        self._pending_scad.clear()
        for desired in pending:
            desired.publish(
                desired.path, desired.content, desired.mtime_ns,
                desired.digest, desired.fingerprint)

    def _merge_generation_sources(self, fresh):
        """Bring the generation union into this phase's one pre-census.

        Sources which predate the phase are observed afresh exactly once.
        A source imported after phase entry already completed the loader's
        pre/post handshake, so it may join by that frozen observation; the
        boundary below still observes it afresh before work is certified.
        """
        for observation in self.generation.observations:
            if observation.path not in self.census._observations:
                if fresh:
                    self.census.include((observation.path,))
                else:
                    self.census.adopt(observation)
            actual = self.census._observations[observation.path]
            if actual != observation:
                raise _changed('phase generation incorporation',
                               observation.path, observation, actual)
        for spelling, expected_real in self.generation._spellings.items():
            actual_real = self.census._canonical_path(spelling)
            if actual_real != expected_real:
                raise _changed('phase source path incorporation', spelling,
                               expected_real, actual_real)

    def include(self, paths):
        observation_start = len(self.census._observation_order)
        spelling_start = len(self.census._spelling_order)
        self.census.include(paths)
        self.generation._remember_phase(
            self.census, observation_start, spelling_start)
        return self

    def checkpoint(self, paths=(), label=None):
        """Patchable boundary used by assembly, waits, and publication."""
        self._merge_generation_sources(fresh=False)
        requested = tuple(paths)
        if requested:
            missing = [path for path in requested if path not in self.census]
            if missing:
                # A contributor may join only through a coherent project
                # import/read or producer-entry include.  Discovering it for
                # the first time after work would bless an unknown epoch.
                raise SourceChanged(
                    f"Project source appeared at {label or self.label}: "
                    f"{os.path.realpath(missing[0])}")
        return self.census.check_current(
            requested, label=label or self.label)


class SourceGeneration:
    """One loaded project/source identity in one interpreter."""

    def __init__(self, root):
        self.root = os.path.realpath(root)
        self._imported = {}
        self._read = {}
        self._phase_sources = {}
        self._spellings = {}
        # Canonical path -> the full identity actually published there now.
        # Historical membership is unsafe: A -> B -> A must publish all three.
        self._scad_artifacts = {}
        self._finder = _ProjectSourceFinder(self)
        self._token = None

    def contains(self, path):
        real = os.path.realpath(path)
        return os.path.commonpath((real, self.root)) == self.root

    @property
    def observations(self):
        merged = dict(self._imported)
        for sources in (self._read, self._phase_sources):
            for path, observation in sources.items():
                existing = merged.get(path)
                if existing is not None and existing != observation:
                    raise _changed('generation source merge', path,
                                   existing, observation)
                merged[path] = observation
        return tuple(merged[path] for path in sorted(merged))

    @property
    def imported_paths(self):
        return frozenset(self._imported)

    def __enter__(self):
        if current_generation() is not None:
            raise RuntimeError('A source generation cannot be nested')
        self._token = _current_generation.set(self)
        sys.meta_path.insert(0, self._finder)
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            if self._finder in sys.meta_path:
                sys.meta_path.remove(self._finder)
        finally:
            _current_generation.reset(self._token)

    def _before_import(self, name, observation):
        self._remember_observation(
            self._imported, observation, f'import {name} pre-execution')

    def _remember_observation(self, destination, observation, label):
        for sources in (self._imported, self._read, self._phase_sources):
            existing = sources.get(observation.path)
            if existing is not None and existing != observation:
                raise _changed(label, observation.path,
                               existing, observation)
        destination[observation.path] = observation

    def _remember_spelling(self, spelling, real, label):
        spelling = os.path.abspath(os.fspath(spelling))
        existing = self._spellings.get(spelling)
        if existing is not None and existing != real:
            raise _changed(label, spelling, existing, real)
        self._spellings[spelling] = real

    def _remember_phase(self, census, observation_start, spelling_start):
        """Freeze every producer contributor into this generation's epoch."""
        for spelling in census._spelling_order[spelling_start:]:
            real = census._spellings[spelling]
            self._remember_spelling(
                spelling, real, 'phase source path incorporation')
        for path in census._observation_order[observation_start:]:
            observation = census._observations[path]
            self._remember_observation(
                self._phase_sources, observation,
                'phase source incorporation')

    def _after_import(self, name, expected):
        try:
            actual = _observe_path(expected.path)
        except OSError:
            raise _changed(f'import {name} post-load', expected.path,
                           expected, None) from None
        if actual != expected:
            raise _changed(f'import {name} post-load', expected.path,
                           expected, actual)

    def coherent_read(self, path):
        data, observation = _coherent_source_bytes(path)
        self._remember_spelling(
            path, observation.path, 'coherent source path')
        self._remember_observation(
            self._read, observation, 'coherent source read')
        try:
            actual = _observe_path(observation.path)
        except OSError:
            raise _changed('coherent source read', observation.path,
                           observation, None) from None
        if actual != observation:
            raise _changed('coherent source read', observation.path,
                           observation, actual)
        return data

    def seal_load(self):
        return self.checkpoint('load post')

    def checkpoint(self, label='generation boundary'):
        for spelling, expected_real in self._spellings.items():
            actual_real = os.path.realpath(spelling)
            if actual_real != expected_real:
                raise _changed(label, spelling, expected_real, actual_real)
        for expected in self.observations:
            try:
                actual = _observe_path(expected.path)
            except OSError:
                raise _changed(label, expected.path, expected, None) from None
            if actual != expected:
                raise _changed(label, expected.path, expected, actual)
        return True

    def phase(self, paths=(), label='phase'):
        return SourcePhase(self, paths, label)

    def has_scad_artifact(self, path, identity):
        """Whether this identity is the path's current published state."""
        if any(value is None for value in identity):
            return False
        return self._scad_artifacts.get(os.path.realpath(path)) == identity

    def remember_scad_artifact(self, path, identity):
        """Record or invalidate the path state after successful publication."""
        canonical = os.path.realpath(path)
        if any(value is None for value in identity):
            self._scad_artifacts.pop(canonical, None)
        else:
            self._scad_artifacts[canonical] = identity


def track_sources(paths):
    """Register a node's known contributors before its producer runs."""
    phase = current_phase()
    if phase is not None:
        phase.include(paths)


def coherent_read(path):
    """Read a foreign source coherently when a generation owns the request."""
    generation = current_generation()
    if generation is None:
        with open(path, 'rb') as source:
            return source.read()
    return generation.coherent_read(path)


def observation_key(path):
    """Strong cache identity for a source read in the current request."""
    census = current_census()
    if census is not None:
        observation = census[path]
    else:
        observation = _observe_path(path)
    return (observation.path, *observation.metadata)


@contextmanager
def consumed_source(path, label='foreign source read'):
    """Tie a path-based foreign reader/cache hit to the active generation.

    Within a producer phase, its shared census supplies the pre-observation
    and the phase exit supplies the uncached post-observation.  Root
    construction may consume a STEP document before any phase exists, so that
    narrower case performs the complete handshake here.
    """
    generation = current_generation()
    phase = current_phase()
    if phase is not None:
        phase.include((path,))
        observation = phase.census[path]
        yield (observation.path, *observation.metadata)
        return

    observation = _observe_path(path)
    if generation is not None:
        generation._remember_spelling(path, observation.path, label)
        generation._remember_observation(
            generation._read, observation, label)
    yield (observation.path, *observation.metadata)
    if generation is not None:
        try:
            actual = _observe_path(path)
        except OSError:
            raise _changed(label, path, observation, None) from None
        if actual != observation:
            raise _changed(label, path, observation, actual)
