import sys
import pyinotify
import asyncio
import traceback
from asyncio import Future
from .loader import load_node
from .git import GitRepo
from .broker import BrokerClient
from solid_node.node.base import StlRenderStart


# Exit codes
BUILD_PRESERVED = 0
BUILD_CHANGED = 1

class Builder(pyinotify.ProcessEvent):
    """Monitors .py files and generate STLs, and exit on any change"""
    def __init__(self, path, debug):
        super().__init__()
        self.path = path
        self.debug = debug

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
        print('Builder start')
        self.broker = BrokerClient()

        async with self.repo.lock():
            try:
                self.node = load_node(self.path)
            except Exception as e:
                error_message = traceback.format_exc()
                await self.rollback(error_message)

            try:
                self.node.assemble()
            except Exception as e:
                error_message = traceback.format_exc()
                await self.rollback(error_message)

            for path in self.node.files:
                mask = pyinotify.IN_CLOSE_WRITE
                self.wm.add_watch(path, mask)

            try:
                await self.generate_stl()
                await self.repo.commit()
            except Exception as e:
                error_message = traceback.format_exc()
                await self.rollback(error_message)

        await self.file_changed
        sys.exit(BUILD_PRESERVED)

    async def generate_stl(self):
        try:
            self.node.trigger_stl()
            return
        except StlRenderStart as job:
            sys.stdout.write(f"Building {job.stl_file}... ")
            sys.stdout.flush()
            job.wait()
            sys.exit(BUILD_CHANGED)

    async def rollback(self, error_message):
        await self.broker.post('compile', error_message)
        await self.repo.discard_changes()
        sys.exit(BUILD_PRESERVED)

    def process_default(self, event):
        if not event.maskname == 'IN_CLOSE_WRITE':
            return
        self.repo.add(event.pathname)
        print(f'{event.pathname} changed, reloading')
        self.file_changed.set_result(True)
