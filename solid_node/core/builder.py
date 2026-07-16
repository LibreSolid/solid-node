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
from asyncio import Future
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .loader import load_node
from solid_node.node.base import StlRenderStart


logger = logging.getLogger('core.builder')


def get_build_dir():
    """Get the base build directory from environment or default"""
    return os.environ.get('SOLID_BUILD_DIR', '_build')


def get_errors_file():
    """Get the path to the errors.json file in the build directory"""
    return os.path.join(get_build_dir(), 'errors.json')


def clear_errors():
    """Clear any existing error file"""
    errors_file = get_errors_file()
    if os.path.exists(errors_file):
        os.remove(errors_file)


def write_error(error_message):
    """Write build error to file for WebViewer to read"""
    errors_file = get_errors_file()
    os.makedirs(os.path.dirname(errors_file), exist_ok=True)
    with open(errors_file, 'w') as f:
        json.dump({
            'error': error_message,
            'tstamp': time.time(),
        }, f)


class Builder(FileSystemEventHandler):
    """Monitors .py files. On any change, generate STLs and exit"""
    def __init__(self, path, is_reload=False):
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

        self.file_changed = Future()
        self.observer = Observer()

    def start(self):
        """Start the rendering process and wait for a file to change, then exits"""
        task = self._start()
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(task)

    async def _start(self):
        logger.info('START')

        try:
            self.node = load_node(self.path)
        except Exception as e:
            await self._on_reload_exception(e, 'load')
            return

        # Clear any previous errors on successful load
        clear_errors()

        try:
            self.node.assemble()
        except Exception as e:
            await self._on_reload_exception(e, 'assemble')
            return

        for path in self.node.files:
            self.observer.schedule(self, path, recursive=False)

        self.observer.start()

        try:
            await self.generate_stl()
        except Exception as e:
            error_message = traceback.format_exc()
            logger.error(error_message)
            await self.report_error(error_message)
            return

        await self.file_changed
        sys.exit(0)

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
            await self.report_error(error_message)
            return

        logger.error(f'{self.path}: failed to {stage} project: {exc}')
        write_error(error_message)
        sys.exit(1)

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
            return
        except StlRenderStart as job:
            logger.info(f"Building {job.stl_file} by pid {job.proc.pid}")
            job.wait()
            logger.info(f"{job.stl_file} done!")
            sys.exit(0)

    async def report_error(self, error_message):
        write_error(error_message)
        await self.file_changed
        sys.exit(0)

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
        if not self.file_changed.done():
            self.file_changed.set_result(True)
