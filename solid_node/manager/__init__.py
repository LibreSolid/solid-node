import os
import sys
import time
import inspect
import asyncio
import argparse
import pyinotify
import traceback
from importlib import import_module
from multiprocessing import Process
from subprocess import Popen



def manage():
    parser = argparse.ArgumentParser(description='Renders solid models into optimized scads and updates on changes')

    parser.add_argument('path', type=str,
                        help='Path of the python source file for a Renderable to work on')

    parser.add_argument('-d', '--debug', action='store_true',
                        help='Debug mode supports breakpoints, but reload is not automatic')
    args = parser.parse_args()

    def openscad():
        from solid_node.viewers.openscad import OpenScadViewer
        OpenScadViewer(args.path).start()


    def monitor(debug=False):
        # Import is done after fork
        from solid_node.manager.monitor import Monitor
        # Avoid racing openscad()
        #time.sleep(0.5)

        task = Monitor(args.path, debug).run()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task)

    scad_proc = Process(target=openscad)
    scad_proc.start()

    if args.debug:
        monitor(True)

    # Run forever if not in debug mode
    while not args.debug:
        p = Process(target=monitor)
        p.start()
        try:
            p.join()
        except KeyboardInterrupt:
            sys.exit(0)

    print(f"Exiting...")
