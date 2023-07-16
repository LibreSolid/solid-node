import os
import asyncio
import traceback
import pyinotify
from asyncio import Future
from solid_node.core import load_node

class Monitor(pyinotify.ProcessEvent):
    """Monitors .py files and generate STLs, and exit on any change"""
    def __init__(self, path, debug):
        super().__init__()

        try:
            self.instance = load_node(path)
        except Exception as e:
            traceback.print_exc()
            self.instance = None

        self.debug = debug

        wm = pyinotify.WatchManager()
        loop = asyncio.get_event_loop()
        pyinotify.AsyncioNotifier(wm, loop, default_proc_fun=self)


        if self.instance:
            try:
                self.instance.assemble()
                print("Rendered!")
            except Exception as e:
                traceback.print_exc()

            mask = pyinotify.IN_CLOSE_WRITE

            for path in self.instance.files:
                print(f'watching {path}')
                wm.add_watch(path, mask)

        self.stl_task = None
        self.future = Future()

    async def run(self):
        self.stl_task = asyncio.create_task(self.generate_stl())
        await self.future

    async def generate_stl(self):
        try:
            self.instance.trigger_stl()
            self.stl_task = None
            print("All STLs built!")
        except StlRenderStart as job:
            sys.stdout.write(f"Building {job.stl_file}... ")
            sys.stdout.flush()
            while job.proc.poll() is None:
                await asyncio.sleep(0.2)
            job.finish()
            print("done, reloading")
            self.bye()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def process_default(self, event):
        if not event.maskname == 'IN_CLOSE_WRITE':
            return
        print(f'{event.pathname} changed, reloading')
        self.bye()

    def bye(self):
        print('BYE!')
        self.future.set_result(None)
