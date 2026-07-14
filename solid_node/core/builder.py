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
    def __init__(self, path):
        super().__init__()
        self.path = path

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
            error_message = traceback.format_exc()
            logger.error(error_message)
            await self.report_error(error_message)
            sys.exit(0)

        # Clear any previous errors on successful load
        clear_errors()

        try:
            self.node.assemble()
        except Exception as e:
            error_message = traceback.format_exc()
            logger.error(error_message)
            await self.report_error(error_message)
            sys.exit(0)

        for path in self.node.files:
            self.observer.schedule(self, path, recursive=False)

        self.observer.start()

        try:
            await self.generate_stl()
        except Exception as e:
            error_message = traceback.format_exc()
            logger.error(error_message)
            await self.report_error(error_message)
            sys.exit(0)

        await self.file_changed
        sys.exit(0)

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
        logger.info(f'{event.src_path} changed, reloading')
        self.loop.call_soon_threadsafe(self.file_changed.set_result, True)
