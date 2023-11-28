import sys
import pyinotify
import asyncio
import traceback
import logging
import time
from asgiref.sync import async_to_sync
from asyncio import Future
from .loader import load_node
from .git import GitRepo
from .broker import BrokerClient
from solid_node.core.refactor import RefactorRequest
from solid_node.node.base import StlRenderStart


logger = logging.getLogger('core.builder')


class Builder(pyinotify.ProcessEvent):
    """Monitors .py files and generate STLs, and exit on any change"""
    def __init__(self, path):
        super().__init__()
        self.path = path

        self.repo = GitRepo(path)
        self.file_changed = Future()
        self.wm = pyinotify.WatchManager()

        loop = asyncio.get_event_loop()
        pyinotify.AsyncioNotifier(self.wm, loop, default_proc_fun=self)

    def start(self):
        task = self._start()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task)

    async def _start(self):
        logger.info('START')
        self.broker = BrokerClient()

        async with self.repo.async_lock('BUILDER'):
            try:
                self.node = load_node(self.path)
            except Exception as e:
                error_message = traceback.format_exc()
                logger.error(error_message)
                await self.rollback(error_message)
                sys.exit(0)

            try:
                self.node.assemble()
            except RefactorRequest as request:
                await self.execute_refactor(request)
            except Exception as e:
                error_message = traceback.format_exc()
                logger.error(error_message)
                await self.rollback(error_message)
                sys.exit(0)

            for path in self.node.files:
                mask = pyinotify.IN_CLOSE_WRITE
                self.wm.add_watch(path, mask)

            try:
                await self.generate_stl()
            except RefactorRequest as request:
                await self.execute_refactor(request)
            except Exception as e:
                error_message = traceback.format_exc()
                logger.error(error_message)
                await self.rollback(error_message)
                sys.exit(0)

        await self.file_changed
        sys.exit(0)

    async def execute_refactor(self, request):
        try:
            request.refactor()
            sys.exit(0)
        except Exception as e:
            error_message = traceback.format_exc()
            logger.error(error_message)
            await self.rollback(f"Could not execute refactor\n\n{error_message}")

    async def generate_stl(self):
        try:
            self.node.trigger_stl()
            return
        except StlRenderStart as job:
            logger.info(f"Building {job.stl_file} by pid {job.proc.pid}")
            job.wait()
            logger.info(f"{job.stl_file} done!")
            sys.exit(0)

    async def rollback(self, error_message):
        await self.broker.put('build_error', {
            'error': error_message,
            'tstamp': time.time(),
        })
        self.repo.revert_last_commit()
        sys.exit(0)

    def process_default(self, event):
        if not event.maskname == 'IN_CLOSE_WRITE':
            return
        logging.info(f'{event.pathname} changed, reloading')
        self.file_changed.set_result(True)
