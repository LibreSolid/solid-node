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
import shutil
import tempfile
import fcntl
import threading
from contextlib import contextmanager
from enum import Enum
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .loader import ProjectManifestError, load_node, project_root
from .serializer import DOCUMENT_FORMAT, DOCUMENT_VERSION, serialize_node
from .pieces import PieceInventory
from solid_node.node.base import StlRenderStart


logger = logging.getLogger('core.builder')


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


def get_build_dir(origin=None):
    """The project's build directory, anchored on the project root.

    A relative `SOLID_BUILD_DIR` -- and the `_build` default -- resolves
    against the discovered project root, never the working directory. A
    project has one build tree and one build lock (the lock path is derived
    from this directory), so resolving it against the caller's cwd would give
    a command run from a subdirectory a private build tree and a private lock:
    artifacts the floor never sees, and mutual exclusion that silently holds
    per-directory instead of per-project.
    """
    configured = os.environ.get('SOLID_BUILD_DIR', '_build')
    if os.path.isabs(configured):
        return configured
    try:
        return os.path.join(project_root(origin), configured)
    except ProjectManifestError:
        # Nothing to anchor on. The caller is about to fail resolving its own
        # reference; do not pre-empt that with a less useful error here.
        return configured


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
    same bounded migration caveat as the previous publication transition.
    """
    build_dir = os.path.abspath(build_dir or get_build_dir())
    parent = os.path.dirname(build_dir) or '.'
    if os.path.islink(build_dir):
        target = os.path.realpath(build_dir)
        os.unlink(build_dir)
        if os.path.exists(target):
            os.replace(target, build_dir)
    os.makedirs(build_dir, exist_ok=True)
    for sibling in os.listdir(parent):
        path = os.path.join(parent, sibling)
        if path != build_dir and sibling.startswith(
                f'{os.path.basename(build_dir)}.'):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    exclude_build_from_git(build_dir)
    return build_dir


def clear_errors(build_dir=None):
    """Clear any existing error file"""
    errors_file = get_errors_file(build_dir)
    if os.path.exists(errors_file):
        os.remove(errors_file)


def write_error(error_message, build_dir=None):
    """Write build error to file for WebViewer to read"""
    errors_file = get_errors_file(build_dir)
    atomic_write(errors_file, json.dumps({
        'error': error_message,
        'tstamp': time.time(),
    }).encode())


class Builder(FileSystemEventHandler):
    """Monitors .py files. On any change, generate STLs and exit"""
    def __init__(self, path, is_reload=False, build_dir=None,
                 watch=True, callback=None,
                 lifecycle=False):
        super().__init__()
        self.path = path

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

        self.file_changed = None
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
        logger.info('START')

        os.environ['SOLID_BUILD_DIR'] = self.build_dir

        try:
            self.node = load_node(self.path)
        except Exception as e:
            return await self._on_reload_exception(e, 'load')

        try:
            self.node.assemble()
        except Exception as e:
            return await self._on_reload_exception(e, 'assemble')

        loaded_source_mtime = self.node.mtime

        if self.watch:
            for path in self.node.files:
                self.observer.schedule(self, path, recursive=False)
            self.observer.start()

        error_message = None
        published = False
        with project_build_lock(self.build_dir):
            prepare_build_dir(self.build_dir)
            # A process may have waited while a newer edit was built. Never
            # let the model it loaded before waiting publish over that result.
            if self.node.mtime != loaded_source_mtime:
                return BuildOutcome.SOURCE_CHANGED
            if self._published_model_is_current():
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
                    published = self._write_viewer_snapshot()
                except Exception:
                    error_message = traceback.format_exc()
                    logger.error(error_message)
            else:
                # A render or publication failure is reported through the
                # error channel rather than escaping the builder process, so
                # the develop loop keeps running and the artifacts already in
                # place stay readable.
                try:
                    outcome = await self.generate_stl()
                    if outcome is BuildOutcome.RENDERED:
                        return outcome
                    self._write_viewer_snapshot()
                    published = True
                except Exception:
                    error_message = traceback.format_exc()
                    logger.error(error_message)
        if error_message:
            return await self.report_error(error_message)
        # Outside the lock: notifying a consumer is not build work, and a
        # callback that blocks must not hold the next builder off.
        if published:
            self._notify_callback()
        if not self.watch:
            return BuildOutcome.CURRENT
        return await self.wait_for_change()

    async def _on_reload_exception(self, exc, stage):
        """Handle an exception raised while (re)importing project
        source -- a module-level SyntaxError, NameError, ImportError,
        anything -- before the observer has had a chance to start (we
        don't yet know self.node.files: that's exactly what failed to
        build).

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
        error_message = traceback.format_exc()

        if self.is_reload:
            logger.error(error_message)
            self._watch_broadly()
            self.observer.start()
            return await self.report_error(error_message)

        logger.error(f'{self.path}: failed to {stage} project: {exc}')
        write_error(error_message, self.build_dir)
        return BuildOutcome.FAILED

    def _watch_broadly(self):
        """Fallback watch for when we don't yet know which files back
        the node (the reload itself failed before we could find out):
        watch the whole project directory recursively so a subsequent
        fix is still detected."""
        watch_dir = os.path.dirname(os.path.realpath(self.path)) or '.'
        self.observer.schedule(self, watch_dir, recursive=True)

    async def generate_stl(self):
        """Trigger the stl generation on the root node, that will recursively render
        stls in all nodes. If in the middle a STL is built, the builder process
        exits to be restarted."""
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
            job.wait()
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

        Returns whether this made anything new reachable, so a build that
        found everything already published notifies nobody.
        """
        os.makedirs(self.build_dir, exist_ok=True)
        inventory = PieceInventory()
        snapshot = {'format': DOCUMENT_FORMAT,
                    'version': DOCUMENT_VERSION,
                    'animation': {'fps': 30, 'frames': 360},
                    'root': serialize_node(
                        self.node,
                        lambda rigid_node: os.path.relpath(
                            rigid_node.stl_file, self.build_dir),
                        inventory.register,
                    )}
        snapshot['pieces'] = inventory.pieces()
        document = json.dumps(snapshot).encode()
        if self._published_document() == document:
            return False
        # An old error must be gone before this manifest exposes new work.
        clear_errors(self.build_dir)
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

        collect(snapshot['root'])
        for root, _, files in os.walk(self.build_dir):
            for filename in files:
                path = os.path.join(root, filename)
                relative = os.path.normpath(os.path.relpath(path,
                                                            self.build_dir))
                if (relative in referenced or filename in ('viewer.json',
                                                            'errors.json') or
                        filename.endswith(
                            ('.scad', '.brep', '.stl.lock', '.tmp'))):
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
        if not event.src_path.endswith('.py') or '__pycache__' in event.src_path:
            # Only relevant under the broad fallback watch (_watch_broadly),
            # which recurses over a whole directory instead of the
            # precise, already-.py-only file list: filter out bytecode
            # cache writes and other noise so they can't trigger a
            # reload loop.
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
