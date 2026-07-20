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
from enum import Enum
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .loader import load_node
from solid_node.node.base import StlRenderStart


logger = logging.getLogger('core.builder')


class BuildOutcome(Enum):
    """The meaningful result of one isolated builder process."""

    CURRENT = 0
    RENDERED = 10
    SOURCE_CHANGED = 11
    FAILED = 1


class BuildSession:
    """A private candidate build directory with an explicit publish step.

    Each builder subprocess receives the same candidate directory until the
    model is current.  The public project build directory only changes when
    that candidate is complete, so a failed reload cannot expose a mixture of
    old and newly generated artifacts.
    """

    def __init__(self, build_dir=None):
        self.build_dir = os.path.abspath(build_dir or get_build_dir())
        self.staging_dir = None
        self.reset()

    def reset(self):
        self.discard()
        parent = os.path.dirname(self.build_dir) or '.'
        os.makedirs(parent, exist_ok=True)
        self.staging_dir = tempfile.mkdtemp(
            prefix='.solid-node-build-', dir=parent)
        if os.path.isdir(self.build_dir):
            shutil.copytree(self.build_dir, self.staging_dir, dirs_exist_ok=True)

    def publish(self):
        """Replace the visible build tree only after a complete build."""
        BuildSessionPublisher(self.staging_dir, self.build_dir).publish()
        self.staging_dir = None

    def discard(self):
        if self.staging_dir and os.path.isdir(self.staging_dir):
            shutil.rmtree(self.staging_dir, ignore_errors=True)
        self.staging_dir = None


def get_build_dir():
    """Get the base build directory from environment or default"""
    return os.environ.get('SOLID_BUILD_DIR', '_build')


def get_errors_file(build_dir=None):
    """Get the path to the errors.json file in the build directory"""
    return os.path.join(build_dir or get_build_dir(), 'errors.json')


def clear_errors(build_dir=None):
    """Clear any existing error file"""
    errors_file = get_errors_file(build_dir)
    if os.path.exists(errors_file):
        os.remove(errors_file)


def write_error(error_message, build_dir=None):
    """Write build error to file for WebViewer to read"""
    errors_file = get_errors_file(build_dir)
    os.makedirs(os.path.dirname(errors_file), exist_ok=True)
    with open(errors_file, 'w') as f:
        json.dump({
            'error': error_message,
            'tstamp': time.time(),
        }, f)


def _viewer_state(node, build_dir):
    state = {
        'name': node.name,
        'type': node._type,
        'color': node.color,
        'mtime': node.mtime,
        'operations': [operation.serialized for operation in node.operations],
    }
    if node.rigid:
        state['model'] = os.path.relpath(node.stl_file, build_dir)
        return state
    children = node.render()
    if type(children) in (list, tuple):
        for child in children:
            node._link_child(child)
        state['children'] = [_viewer_state(child, build_dir) for child in children]
    return state


class Builder(FileSystemEventHandler):
    """Monitors .py files. On any change, generate STLs and exit"""
    def __init__(self, path, is_reload=False, build_dir=None,
                 published_build_dir=None, watch=True, callback=None,
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
        self.build_dir = build_dir
        self.published_build_dir = published_build_dir or build_dir
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

        if self.build_dir is not None:
            os.environ['SOLID_BUILD_DIR'] = self.build_dir

        try:
            self.node = load_node(self.path)
        except Exception as e:
            return await self._on_reload_exception(e, 'load')

        # Clear any previous errors on successful load
        clear_errors(self.published_build_dir)

        try:
            self.node.assemble()
        except Exception as e:
            return await self._on_reload_exception(e, 'assemble')

        if self.watch:
            for path in self.node.files:
                self.observer.schedule(self, path, recursive=False)
            self.observer.start()

        try:
            outcome = await self.generate_stl()
        except Exception as e:
            error_message = traceback.format_exc()
            logger.error(error_message)
            return await self.report_error(error_message)

        if outcome is BuildOutcome.RENDERED:
            return outcome

        self._write_viewer_snapshot()
        self._publish()
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
        write_error(error_message, self.published_build_dir)
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
            return BuildOutcome.CURRENT
        except StlRenderStart as job:
            logger.info(f"Building {job.stl_file} by pid {job.proc.pid}")
            job.wait()
            logger.info(f"{job.stl_file} done!")
            return BuildOutcome.RENDERED

    async def report_error(self, error_message):
        write_error(error_message, self.published_build_dir)
        if not self.watch:
            return BuildOutcome.FAILED
        return await self.wait_for_change()

    async def wait_for_change(self):
        if self.file_changed is None:
            self.file_changed = asyncio.get_running_loop().create_future()
        if not self.file_changed.done():
            await self.file_changed
        return BuildOutcome.SOURCE_CHANGED

    def _publish(self):
        if self.build_dir is None or self.published_build_dir is None:
            return
        BuildSessionPublisher(self.build_dir, self.published_build_dir).publish()

    def _write_viewer_snapshot(self):
        """Record the source-backed viewer tree beside a completed build."""
        if self.build_dir is None:
            return
        os.makedirs(self.build_dir, exist_ok=True)
        with open(os.path.join(self.build_dir, 'viewer.json'), 'w') as snapshot:
            json.dump({'version': 1,
                       'root': _viewer_state(self.node, self.build_dir)}, snapshot)

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


class BuildSessionPublisher:
    """Publish a candidate directory from a builder child process."""

    def __init__(self, staging_dir, build_dir):
        self.staging_dir = staging_dir
        self.build_dir = build_dir

    def publish(self):
        previous = None
        if os.path.lexists(self.build_dir):
            previous = tempfile.mktemp(
                prefix='.solid-node-previous-',
                dir=os.path.dirname(self.build_dir) or '.')
            os.replace(self.build_dir, previous)
        try:
            os.replace(self.staging_dir, self.build_dir)
        except Exception:
            if previous is not None and not os.path.lexists(self.build_dir):
                os.replace(previous, self.build_dir)
            raise
        if previous is not None:
            shutil.rmtree(previous, ignore_errors=True)
