import os
import sys
import time
import inspect
import asyncio
import argparse
import pyinotify
import traceback
from importlib import import_module
from solid_node.node.base import AbstractBaseNode, StlRenderStart
from multiprocessing import Process
from subprocess import Popen


OPENSCAD_PID = ".openscad.pid"


def bye(code=0, terminate_scad=False):
    if terminate_scad:
        pid = open(OPENSCAD_PID).read()
        os.kill(int(pid), 15)
        os.remove(OPENSCAD_PID)
    sys.exit(code)


class Monitor(pyinotify.ProcessEvent):
    """Monitors .py files and generate STLs, and exit on any change"""
    def __init__(self, path, debug):
        super().__init__()
        error = None
        try:
            self.instance = instantiate_path(path)
        except Exception as e:
            traceback.print_exc()
            self.instance = None
            error = True

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
                error = True

        mask = pyinotify.IN_CLOSE_WRITE

        for path in self.instance.files:
            print(f'watching {path}')
            wm.add_watch(path, mask)

        self.stl_task = asyncio.create_task(self.generate_stl())

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
            bye(0, self.debug)
        except Exception as e:
            import traceback
            traceback.print_exc()

    def process_default(self, event):
        if not event.maskname == 'IN_CLOSE_WRITE':
            return
        print(f'{event.pathname} changed, reloading')
        bye(0, self.debug)


def instantiate_path(path):
    if not path.endswith('.py'):
        raise Exception("Can only load .py files")

    path = os.path.realpath(path)
    relative_path = os.path.relpath(path)
    module_name = relative_path.replace('/', '.')[:-3]

    module = import_module(module_name)

    for name, klass in module.__dict__.items():
        if isinstance(klass, type) and issubclass(klass, AbstractBaseNode) \
           and inspect.getfile(klass) == path:
            return klass()


async def start_watch(path, debug):
    Monitor(path, debug)
    while True:
        await asyncio.sleep(1)


def manage():
    parser = argparse.ArgumentParser(description='Renders solid models into optimized scads and updates on changes')

    parser.add_argument('path', type=str,
                        help='Path of the python source file for a Renderable to work on')

    parser.add_argument('-d', '--debug', action='store_true',
                        help='Debug mode supports breakpoints, but reload is not automatic')
    args = parser.parse_args()

    def openscad():
        instance = instantiate_path(args.path)
        proc = Popen(['openscad', instance.scad_file])
        if args.debug:
            open(OPENSCAD_PID, 'w').write(f'{proc.pid}')


    def monitor(debug=False):
        time.sleep(0.5)  # avoid racing openscad()
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(start_watch(args.path, debug))

        except KeyboardInterrupt:
            bye(-2)

    scad_proc = Process(target=openscad)
    scad_proc.start()

    if args.debug:
        monitor(True)

    exit_code = 0
    while exit_code >= 0:
        p = Process(target=monitor)
        p.start()
        try:
            p.join()
        except KeyboardInterrupt:
            bye(-1)


    print(f"Exiting...")
