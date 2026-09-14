# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import json
import asyncio
import traceback
import logging
import time
import tempfile
import fcntl
import threading
from contextlib import contextmanager
from enum import Enum
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .loader import (ProjectManifestError, load_node,
                     project_root, project_source_generation, read_project)
from .serializer import (
    compiled_program, document_body,
    DOCUMENT_FORMAT, drivers_table, instructions_table,
    serialize_node, symbolic_document,
)
from . import pieces
from .pieces import PieceInventory
from solid_node._artifact import ArtifactChanged
from solid_node import currency
from solid_node.node.base import StlRenderStart
from solid_node.source_generation import (SourceChanged, current_phase)
from solid_node.viewers import bundle as viewer_bundle


logger = logging.getLogger('core.builder')


def _warn_unreadable(version):
    """Say, once, that the installed viewer cannot read the document just
    published -- and publish it anyway.

    `solid develop` serves it and the browser refuses it BY NAME, which is
    the designed behaviour: the build, the STLs and the tests are still
    useful, and `--no-web` is unaffected.
    """
    message = viewer_bundle.unreadable_document(version)
    if message is not None:
        logger.warning(
            f'{message}. The document is published anyway: the build, its '
            f'artifacts, the tests and a viewerless watch loop are '
            f'unaffected by a browser that cannot render, and the '
            f"document's own refusal is the consumer's to make.")


_build_locks = threading.local()


def get_build_lock_path(build_dir=None):
    """Return the project-scoped lock beside the published build path."""
    return f'{os.path.abspath(build_dir or get_build_dir())}.lock'


@contextmanager
def project_build_lock(build_dir=None):
    """Serialize artifact producers for one published build directory.

    ``flock`` is deliberately advisory: every framework producer takes this
    lock, while readers remain free to consume the currently published build.
    The descriptor is opened by the acquiring process, so it is never inherited
    by a builder child. Re-entry on the same thread shares that descriptor.
    """
    path = get_build_lock_path(build_dir)
    held = getattr(_build_locks, 'held', {})
    entry = held.get(path)
    if entry:
        entry['depth'] += 1
        try:
            yield
        finally:
            entry['depth'] -= 1
        return

    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    exclude_build_from_git(build_dir or get_build_dir())
    handle = open(path, 'a+')
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.info('Waiting for project build lock %s', path)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        held[path] = {'handle': handle, 'depth': 1}
        _build_locks.held = held
        yield
    finally:
        entry = held.get(path)
        if entry:
            entry['depth'] -= 1
            if entry['depth'] == 0:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()
                del held[path]


class BuildOutcome(Enum):
    """The meaningful result of one isolated builder process."""

    CURRENT = 0
    RENDERED = 10
    SOURCE_CHANGED = 11
    FAILED = 1


#: The build directory a command selected for this process, as
#: `(build root, build dir)`, or None. See `anchor_build_dir`.
_anchor = None


def _anchored():
    """The selection, while the environment still carries it.

    The environment is the anchor -- it is what a fresh interpreter inherits
    -- and this record only remembers the root it was derived from. When
    something restores the environment, as every test that runs a command
    in-process does, the record no longer describes the process and is
    ignored rather than left to point at a directory that is gone.
    """
    if _anchor is not None and os.environ.get('SOLID_BUILD_DIR') == _anchor[1]:
        return _anchor
    return None


def project_build_root(origin=None):
    """The project's build root, anchored on the project root.

    A relative `SOLID_BUILD_DIR` -- and the `_build` default -- resolves
    against the discovered project root, never the working directory. A
    project has one build root, so resolving it against the caller's cwd
    would give a command run from a subdirectory a private build tree and
    a private lock: artifacts the floor never sees, and mutual exclusion
    that silently holds per-directory instead of per-project.
    """
    anchored = _anchored()
    if anchored is not None:
        return anchored[0]
    configured = os.environ.get('SOLID_BUILD_DIR', '_build')
    if os.path.isabs(configured):
        return configured
    try:
        return os.path.join(project_root(origin), configured)
    except ProjectManifestError:
        # Nothing to anchor on. The caller is about to fail resolving its own
        # reference; do not pre-empt that with a less useful error here.
        return configured


def get_build_dir(origin=None):
    """The build directory this process writes into.

    The build root, unless a command selected a project model: a declared
    model owns `<build root>/<name>`, and everything per build directory --
    the published document, the errors file, the lock, the sweep -- then
    happens there.
    """
    anchored = _anchored()
    if anchored is not None:
        return anchored[1]
    return project_build_root(origin)


def anchor_build_dir(build_root, build_dir):
    """Select `build_dir` for this process and, through the environment,
    for every fresh interpreter it starts (ADR-067).

    The root is remembered beside it so a later selection in the same
    process -- `solid test --all` walking the models -- starts from the
    project's root again rather than nesting under the directory anchored
    last.
    """
    global _anchor
    _anchor = (os.path.abspath(build_root), os.path.abspath(build_dir))
    os.environ['SOLID_BUILD_DIR'] = _anchor[1]


def unanchor_build_dir():
    """Forget the selection. For tests, which share one process."""
    global _anchor
    _anchor = None


def get_errors_file(build_dir=None):
    """Get the path to the errors.json file in the build directory"""
    return os.path.join(build_dir or get_build_dir(), 'errors.json')


def atomic_write(path, content):
    """Replace one artifact without ever exposing a partial file."""
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


def prepare_build_dir(build_dir=None):
    """Migrate an ADR-032 symlink once, then return a real build directory.

    The caller holds the project build lock. This one-time conversion has the
    same bounded migration caveat as the previous publication transition. The
    referenced target is the only sibling the symlink proves belongs to this
    build; every other sibling is left alone.
    """
    build_dir = os.path.abspath(build_dir or get_build_dir())
    if os.path.islink(build_dir):
        target = os.path.realpath(build_dir)
        os.unlink(build_dir)
        if os.path.exists(target):
            os.replace(target, build_dir)
    os.makedirs(build_dir, exist_ok=True)
    exclude_build_from_git(build_dir)
    return build_dir


def clear_errors(build_dir=None):
    """Clear any existing error file and report a recovered failure state."""
    errors_file = get_errors_file(build_dir)
    if os.path.exists(errors_file):
        os.remove(errors_file)
        return True
    return False


def write_error(error_message, build_dir=None):
    """Write build error to file for WebViewer to read"""
    errors_file = get_errors_file(build_dir)
    atomic_write(errors_file, json.dumps({
        'error': error_message,
        'tstamp': time.time(),
    }).encode())


class Builder(FileSystemEventHandler):
    """Monitor model sources. On any relevant change, exit for a rebuild."""
    def __init__(self, path, is_reload=False, build_dir=None,
                 watch=True, callback=None,
                 lifecycle=False, overrides=None, scad_output=True):
        super().__init__()
        self.path = path
        # The root's `--set` words, carried into every load this builder
        # performs so a develop session's reloads keep the parameters it
        # was started with.
        self.overrides = list(overrides or [])

        # True for every attempt after the very first: an exception
        # while (re)importing project source on this path is treated as
        # a recoverable build failure, not a fatal one (see
        # _on_reload_exception below). The very first attempt for a
        # `solid develop` invocation keeps the old, non-surviving
        # behavior -- a broken project at launch exits with a clear
        # error instead of looping.
        self.is_reload = is_reload
        self.build_dir = os.path.abspath(build_dir or get_build_dir())
        self.watch = watch
        self.callback = callback
        self.lifecycle = lifecycle
        self.scad_output = scad_output

        self.file_changed = None
        self._watched_sources = set()
        self._broad_python_watch = None
        self.observer = Observer()

    def start(self):
        """Start the rendering process and wait for a file to change, then exits"""
        task = self._start()
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        self.file_changed = self.loop.create_future()
        outcome = self.loop.run_until_complete(task)
        self.observer.stop()
        if self.observer.is_alive():
            self.observer.join()
        if not self.lifecycle and outcome in (
                BuildOutcome.RENDERED, BuildOutcome.SOURCE_CHANGED):
            sys.exit(0)
        sys.exit(outcome.value)

    async def _start(self):
        # The public/test-facing coroutine keeps one entry point, while the
        # recursive call below lets the existing body run wholly inside the
        # generation context without indenting every outcome path.  A mocked
        # loader test may name no real project; in that case its old behavior
        # remains available and the patched load decides the result.
        if '_source_generation' not in self.__dict__:
            try:
                context = project_source_generation(self.path)
            except ProjectManifestError:
                context = None
            if context is None:
                self._source_generation = None
                try:
                    return await self._start()
                finally:
                    del self._source_generation
            with context as generation:
                self._source_generation = generation
                try:
                    return await self._start()
                finally:
                    del self._source_generation

        logger.info('START')

        os.environ['SOLID_BUILD_DIR'] = self.build_dir

        try:
            self.node = load_node(
                self.path, overrides=self.overrides,
                generation=self._source_generation)
        except SourceChanged:
            return BuildOutcome.SOURCE_CHANGED
        except Exception as e:
            return await self._on_reload_exception(e, 'load')

        # Remember the source state represented by the classes load_node()
        # imported. If this process waits for another producer and those files
        # move meanwhile, it must stand down before the stale classes render.
        try:
            if self._source_generation is None:
                loaded_source_mtime_ns = self.node.mtime_ns
            else:
                # Freeze the root's complete initially known closure before
                # this process can wait for the project lock.  A foreign
                # contributor replaced beneath the same maximum must disagree
                # with this loaded generation at `after_lock`, not be first
                # observed there and accidentally blessed.
                with self._source_generation.phase(
                        self.node.files, label='loaded_sources'):
                    loaded_source_mtime_ns = self.node.mtime_ns
        except SourceChanged:
            return BuildOutcome.SOURCE_CHANGED
        except Exception as error:
            # This source set has not been observed before, so a missing or
            # unreadable contributor is a load/preflight failure rather than a
            # change to an established generation.  Preserve the existing
            # one-shot failure and reload-repair behavior outside the lock.
            return await self._on_reload_exception(
                error, 'inspect initial sources')
        assembly_failure = None
        error_message = None
        published = False
        with project_build_lock(self.build_dir):
            prepare_build_dir(self.build_dir)
            if self._source_generation is not None:
                try:
                    self._source_generation.checkpoint('after_lock')
                except SourceChanged:
                    return BuildOutcome.SOURCE_CHANGED
            # A process may have waited while a newer edit was built. Never
            # let the model it loaded before waiting render over that result.
            if self.node.mtime_ns != loaded_source_mtime_ns:
                return BuildOutcome.SOURCE_CHANGED

            try:
                # Preparation discovers structure and lets native adapters
                # materialize without constructing an assembly-wide SCAD tree.
                if self._source_generation is None:
                    self.node._prepare()
                else:
                    with self._source_generation.phase(
                            self.node.files, label='assembly'):
                        self.node._prepare()
            except SourceChanged:
                return BuildOutcome.SOURCE_CHANGED
            except Exception as error:
                # A reload failure may wait for a repair. Carry its traceback
                # out so that wait happens only after the lock is released.
                assembly_failure = (error, traceback.format_exc())

            # Assembly discovers the complete source union. An edit during it
            # invalidates the loaded classes before any later publication.
            if (assembly_failure is None and
                    self.node.mtime_ns != loaded_source_mtime_ns):
                return BuildOutcome.SOURCE_CHANGED

            if assembly_failure is None and self.watch:
                self._watched_sources = {
                    os.path.realpath(path) for path in self.node.files
                }
                for path in self.node.files:
                    self.observer.schedule(self, path, recursive=False)
                self.observer.start()

            current = False
            if assembly_failure is None:
                try:
                    if self._source_generation is None:
                        current = self._published_model_is_current()
                    else:
                        with self._source_generation.phase(
                                self.node.files, label='artifact_currency'):
                            current = self._published_model_is_current()
                except SourceChanged:
                    return BuildOutcome.SOURCE_CHANGED

            if assembly_failure is None and current:
                # No artifact needs rendering -- but the document naming them
                # may still be a build behind, because the pass that rendered
                # an artifact exits before writing it and the next pass finds
                # that artifact current.  Nothing else republishes it, so a
                # consumer would keep reading the previous model's manifest.
                #
                # This builder is also not finished: a watching builder still
                # has to wait for the next source change below; returning here
                # would exit it at once and spin the develop loop respawning
                # it.
                logger.info('Published artifacts are already current')
                try:
                    self._present_scad_if_requested()
                    if self._source_generation is None:
                        published = self._write_viewer_snapshot()
                    else:
                        with self._source_generation.phase(
                                self.node.files, label='publication'):
                            published = self._write_viewer_snapshot()
                except SourceChanged:
                    return BuildOutcome.SOURCE_CHANGED
                except Exception:
                    error_message = traceback.format_exc()
                    logger.error(error_message)
            elif assembly_failure is None:
                # A render or publication failure is reported through the
                # error channel rather than escaping the builder process, so
                # the develop loop keeps running and the artifacts already in
                # place stay readable.
                try:
                    while True:
                        if self._source_generation is None:
                            outcome = await self.generate_stl()
                        else:
                            # A retained pass gets a new census.  It may reuse
                            # this loaded and assembled tree, never the prior
                            # pass's observation of its contributors.
                            with self._source_generation.phase(
                                    self.node.files, label='artifact_pass'):
                                outcome = await self.generate_stl()
                        if outcome is not BuildOutcome.RENDERED:
                            break
                        if not getattr(self, '_artifact_pass_progressed', False):
                            # `trigger_stl()` also returns without starting a
                            # renderer while another producer owns the
                            # per-STL lock.  Retrying that state in this child
                            # would spin under the project lock.  Preserve the
                            # supervisor retry boundary for that no-progress
                            # result; only a renderer this child completed may
                            # continue the retained generation.
                            return outcome
                    self._present_scad_if_requested()
                    if self._source_generation is None:
                        self._write_viewer_snapshot()
                    else:
                        with self._source_generation.phase(
                                self.node.files, label='publication'):
                            self._write_viewer_snapshot()
                    published = True
                except SourceChanged:
                    return BuildOutcome.SOURCE_CHANGED
                except Exception:
                    error_message = traceback.format_exc()
                    logger.error(error_message)
        if assembly_failure is not None:
            error, error_traceback = assembly_failure
            return await self._on_reload_exception(
                error, 'assemble', error_traceback)
        if error_message:
            return await self.report_error(error_message)
        # Outside the lock: notifying a consumer is not build work, and a
        # callback that blocks must not hold the next builder off.
        if published:
            self._notify_callback()
        if not self.watch:
            return BuildOutcome.CURRENT
        return await self.wait_for_change()

    def _present_scad_if_requested(self):
        """Publish compatibility SCAD only for a consumer that requested it."""
        if not self.scad_output:
            return
        if self._source_generation is None:
            self.node.assemble()
            return
        with self._source_generation.phase(self.node.files, label='assembly'):
            self.node.assemble()

    async def _on_reload_exception(self, exc, stage, error_message=None):
        """Handle an exception raised while (re)importing project
        source -- a module-level SyntaxError, NameError, ImportError,
        anything -- before the observer has had a chance to start.  A load
        failure has no node/file set; an initial-census failure already has
        one, including the missing foreign path that a repair may recreate.

        On the WATCH-LOOP reload path (self.is_reload) this must NOT
        take the develop process down: fall back to watching the whole
        project directory (broadly, since the precise file list isn't
        known), surface the error through the same errors.json channel
        build failures already use, and exit cleanly the instant a
        subsequent save is noticed so Develop's loop can respawn and
        retry.

        On initial startup (not a reload) a broken project keeps
        failing fast: log one clean line (not a full traceback dump)
        and exit with a non-zero status instead of hanging forever
        with nothing watching.
        """
        error_message = error_message or traceback.format_exc()

        if self.is_reload:
            logger.error(error_message)
            self._watch_broadly(
                getattr(getattr(self, 'node', None), 'files', ()))
            self.observer.start()
            return await self.report_error(error_message)

        logger.error(f'{self.path}: failed to {stage} project: {exc}')
        write_error(error_message, self.build_dir)
        return BuildOutcome.FAILED

    def _watch_broadly(self, known_sources=()):
        """Fallback watch for when we don't yet know which files back
        the node (the reload itself failed before we could find out):
        watch the entry directory recursively so a subsequent Python fix is
        still detected.  An initial-census failure may additionally name a
        missing foreign contributor outside that subtree; subscribe to the
        smallest existing parent that can observe its repair, while the event
        filter continues to admit only that exact foreign path."""
        self._watched_sources = {
            os.path.realpath(path) for path in known_sources
        }
        self._broad_python_watch = (
            os.path.dirname(os.path.realpath(self.path)) or '.')

        def existing_parent(path):
            directory = os.path.dirname(path) or '.'
            while not os.path.isdir(directory):
                parent = os.path.dirname(directory)
                if parent == directory:
                    break
                directory = parent
            return os.path.realpath(directory)

        def covered(path, directory):
            try:
                return os.path.commonpath((path, directory)) == directory
            except ValueError:
                return False

        candidates = {self._broad_python_watch}
        candidates.update(existing_parent(path)
                          for path in self._watched_sources)
        watch_dirs = []
        # Shallower candidates cover their descendants.  This matters when a
        # missing contributor's parent is itself absent: its nearest existing
        # ancestor may already cover the entry subtree.
        for candidate in sorted(
                candidates,
                key=lambda path: (len(os.path.normpath(path).split(os.sep)),
                                  path)):
            if any(covered(candidate, directory)
                   for directory in watch_dirs):
                continue
            watch_dirs.append(candidate)
        for watch_dir in watch_dirs:
            self.observer.schedule(self, watch_dir, recursive=True)

    async def generate_stl(self):
        """Perform one sequential artifact pass on the assembled root.

        ``RENDERED`` means either that this child completed one asynchronous
        renderer, in which case ``_start`` may safely continue, or that no
        renderer could start because a per-STL lock is live.  The private
        progress bit distinguishes those lifecycle meanings without widening
        the process-level ``BuildOutcome`` contract.
        """
        self._artifact_pass_progressed = False
        try:
            self.node.trigger_stl()
            if not self._artifacts_are_current():
                # Another builder may own a node's per-STL render lock.  In
                # that case generate_stl() deliberately does nothing, but the
                # missing artifact is not a complete build: make the
                # supervisor retry instead of running publication checks.
                return BuildOutcome.RENDERED
            return BuildOutcome.CURRENT
        except StlRenderStart as job:
            logger.info(f"Building {job.stl_file} by pid {job.proc.pid}")
            phase = current_phase()
            job.wait(checkpoint=phase.checkpoint if phase is not None else None)
            self._artifact_pass_progressed = True
            logger.info(f"{job.stl_file} done!")
            return BuildOutcome.RENDERED

    async def report_error(self, error_message):
        write_error(error_message, self.build_dir)
        if not self.watch:
            return BuildOutcome.FAILED
        return await self.wait_for_change()

    async def wait_for_change(self):
        if self.file_changed is None:
            self.file_changed = asyncio.get_running_loop().create_future()
        if not self.file_changed.done():
            await self.file_changed
        return BuildOutcome.SOURCE_CHANGED

    def _write_viewer_snapshot(self):
        """Record the source-backed viewer tree beside a completed build.

        Returns whether externally visible publication state changed. A new
        document or recovery from a prior error is observable; a build that
        found the same successful state already published notifies nobody.

        Serialized in symbolic driver mode, the same guarantee export
        makes: the published document describes the machine, not the
        pose whatever bound a snapshot last happened to leave it in.
        """
        for attempt in range(3):
            try:
                with PieceInventory() as inventory:
                    return self._write_viewer_snapshot_with_inventory(inventory)
            except ArtifactChanged:
                if attempt == 2:
                    raise

    def _write_viewer_snapshot_with_inventory(self, inventory):
        """Serialize while artifact snapshots stay pinned through publish."""
        os.makedirs(self.build_dir, exist_ok=True)
        # Compiled off the NUMERIC rest render, before the symbolic walk,
        # and `(None, None)` under any root but a running one.
        program, initial = compiled_program(self.node)
        with symbolic_document(self.node) as (declarations, instructions):
            root = serialize_node(
                self.node,
                lambda rigid_node: os.path.relpath(
                    rigid_node.stl_file, self.build_dir),
                inventory.register,
                graph_values=True,
            )
            drivers = drivers_table(declarations)
            events = instructions_table(instructions,
                                        running=program is not None)
        # The version its content needs, or 5 where the ROOT declares a
        # running base; `bindings` and `program` beside `drivers` and
        # `instructions`, ahead of `root`, and deterministically ordered
        # (design.md D5) -- which is what keeps the byte comparison below
        # correct: rebuilding an unchanged model must not republish
        # merely because a name was minted differently.
        snapshot = document_body(self.node, root, drivers, events,
                                 program, initial)
        snapshot['root'] = root
        snapshot['pieces'] = inventory.pieces()
        _warn_unreadable(snapshot['version'])
        document = json.dumps(snapshot).encode()
        phase = current_phase()
        if phase is not None:
            # Serialization may execute project getters and source-backed
            # piece work.  Recheck after all of it and immediately before the
            # manifest becomes externally reachable.
            phase.checkpoint(
                self.node.files, label='publication_pre_write')
        inventory.validate()
        recovered = clear_errors(self.build_dir)
        if self._published_document() == document:
            return recovered
        # An old error must be gone before this manifest exposes new work.
        atomic_write(os.path.join(self.build_dir, 'viewer.json'), document)
        self._sweep_unreferenced_artifacts(snapshot)
        return True

    def _published_document(self):
        try:
            with open(os.path.join(self.build_dir, 'viewer.json'), 'rb') as f:
                return f.read()
        except OSError:
            return None

    def _published_model_is_current(self):
        """Whether the publication already covers this loaded source state.

        Every rigid artifact is checked where a consumer reads it, together
        with the manifest that makes those artifacts reachable.
        """
        if (not self.build_dir or
                not os.path.isfile(os.path.join(self.build_dir,
                                                'viewer.json'))):
            return False

        return self._artifacts_are_current()

    def _artifacts_are_current(self):
        """Whether every rigid artifact in the loaded tree is current."""

        def current(node):
            if node.rigid and not node._up_to_date(
                    node.stl_file):
                return False
            if (node.rigid and getattr(node, 'exact', False)
                    and not node._up_to_date(node.brep_file)):
                return False
            return all(current(child) for child in node.children)

        return current(self.node)

    def _sweep_unreferenced_artifacts(self, snapshot):
        referenced = set()

        def collect(node):
            if 'model' in node:
                referenced.add(os.path.normpath(node['model']))
            for child in node.get('children', []):
                collect(child)

        def collect_snapshots(node):
            """The per-binding artifacts the assembled tree imports.

            A flexible leaf's snapshot is addressed by its binding as well
            as by the node, and the published document is serialized
            symbolically -- it describes the machine, not the pose -- so
            the document cannot name the file the assembled SCAD actually
            imports. The tree can, and it is the same tree this
            publication describes. Every other binding's snapshot is
            therefore unreferenced, which is exactly what the sweep
            collects.
            """
            artifact = getattr(node, 'snapshot_file', None)
            if artifact:
                referenced.add(os.path.normpath(
                    os.path.relpath(artifact, self.build_dir)))
            for child in getattr(node, 'children', ()):
                collect_snapshots(child)

        def kept(relative, filename):
            # `.lock` spares a declared model's build lock, which lies inside
            # the build root: unlinking a held lock's path would let the next
            # acquirer open a fresh inode and lock nothing.
            return (relative in referenced or
                    filename in ('viewer.json', 'errors.json') or
                    filename.endswith(('.scad', '.brep', '.stl.lock',
                                       '.lock', '.tmp')))

        collect(snapshot['root'])
        collect_snapshots(self.node)
        # A declared model's directory is its own to sweep: the build root's
        # walk does not descend into one.
        try:
            model_names = set(read_project(self.build_dir).names)
        except ProjectManifestError:
            # A build directory with no project above it declares nothing.
            model_names = set()
        for root, directories, files in os.walk(self.build_dir):
            if root == self.build_dir:
                directories[:] = [name for name in directories
                                  if name not in model_names]
            for filename in files:
                path = os.path.join(root, filename)
                relative = os.path.normpath(os.path.relpath(path,
                                                            self.build_dir))
                # A source digest is not an artifact and is never named by
                # the document, so it is judged by the artifact it vouches
                # for rather than on its own. Sweeping them all -- which
                # is what the unreferenced rule below would do -- leaves
                # every build working and the content-verified fallback
                # permanently off, with nothing to notice it by.
                described = currency.describes(relative)
                if described is None:
                    described = pieces.describes(relative)
                if described is not None:
                    if not kept(described, os.path.basename(described)):
                        os.remove(path)
                    continue
                if kept(relative, filename):
                    continue
                os.remove(path)

    def _notify_callback(self):
        if not self.callback:
            return
        try:
            import httpx
            response = httpx.post(self.callback, content=b'', timeout=2.0)
            response.raise_for_status()
        except Exception as exc:
            logger.warning('Build-ready callback failed for %s: %s',
                           self.callback, exc)


    def on_modified(self, event):
        """Called when a file is modified, sets the result of the awaiting future
        for the process to exit"""
        if event.is_directory:
            return
        source = os.path.realpath(event.src_path)
        known_source = source in self._watched_sources
        broad_python = (source.endswith('.py') and
                        '__pycache__' not in source)
        if (broad_python and self._broad_python_watch is not None):
            try:
                broad_python = (os.path.commonpath(
                    (source, self._broad_python_watch)) ==
                    self._broad_python_watch)
            except ValueError:
                broad_python = False
        if not known_source and not broad_python:
            # A precisely watched path is already known to affect the model,
            # whatever its extension. Events outside that set can only come
            # from recovery subscriptions, where unrelated foreign files,
            # Python outside the original broad area, and bytecode writes
            # must not trigger a reload loop.
            return
        logger.info(f'{event.src_path} changed, reloading')
        self.loop.call_soon_threadsafe(self._resolve_file_changed)

    def _resolve_file_changed(self):
        # Guard against a second filesystem event arriving before the
        # first has been consumed (e.g. an editor's atomic-write
        # touching more than one path under the broad fallback watch).
        if self.file_changed is not None and not self.file_changed.done():
            self.file_changed.set_result(True)


def exclude_build_from_git(build_dir):
    """Keep published artifacts out of `git status` without touching a
    tracked file.

    The build path is an ordinary directory, but a project may still hold
    the lock file this build writes beside it, and a project converted from
    the previous layout may hold leftovers, so the pattern covers siblings
    as well. `.gitignore` is tracked, so writing to it
    during a build would dirty the working tree at an arbitrary moment
    and could be swept into an unrelated commit; `.git/info/exclude` is
    local, invisible to `git status`, and cannot be committed.

    Only acts when the project's own `.gitignore` does not already carry
    the pattern, and only when `.git` is a real directory -- in a
    worktree or submodule it is a file pointing elsewhere, and finding
    the real one would mean running git from the build path. Every
    failure is ignored: publication matters, this does not.
    """
    parent = os.path.dirname(os.path.abspath(build_dir))
    pattern = f'{os.path.basename(build_dir)}*'
    try:
        gitignore = os.path.join(parent, '.gitignore')
        if os.path.isfile(gitignore):
            with open(gitignore) as handle:
                if pattern in handle.read().split():
                    return

        info = os.path.join(parent, '.git', 'info')
        if not os.path.isdir(info):
            return
        exclude = os.path.join(info, 'exclude')
        if os.path.isfile(exclude):
            with open(exclude) as handle:
                if pattern in handle.read().split():
                    return
        with open(exclude, 'a') as handle:
            handle.write(f'{pattern}\n')
    except OSError as error:
        logger.debug('Could not record the build exclusion for %s: %s',
                     build_dir, error)
