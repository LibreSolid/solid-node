import os
import sys
import time
import socket
import inspect
import logging
import asyncio
import traceback
from importlib import import_module
from multiprocessing import Process
from subprocess import Popen
from solid_node.core import load_node
from solid_node.core.broker import (BrokerServer,
                                    BrokerClient,
                                    HOST as BROKER_HOST,
                                    PORT as BROKER_PORT)
from solid_node.core.builder import Builder
from solid_node.core.git import GitRepo
from solid_node.node.base import StlRenderStart
from solid_node.viewers.openscad import OpenScadViewer
from solid_node.viewers.web import WebViewer, WebDevServer


logger = logging.getLogger('manager.develop')


class Develop:
    """Monitor filesystem and executes transpilations and compilations on background"""

    def add_arguments(self, parser):
        parser.add_argument('--web', action='store_true',
                            help='Start a webserver to view project in browser (default)')
        parser.add_argument('--web-dev', action='store_true',
                            help='Start a development webserver (proxy to npm start) to view project in browser')
        parser.add_argument('--openscad', action='store_true',
                            help='Show project in OpenSCAD')
        parser.add_argument('--debug-builder', action='store_true',
                            help='Debug mode supports breakpoints, but reload is not automatic')
        parser.add_argument('--debug-web', action='store_true',
                            help='Debug mode to support breakpoints in webserver')


    def openscad(self):
        OpenScadViewer(self.path).start()

    def web(self):
        WebViewer(self.path, self.web_dev).start()

    def web_dev_server(self):
        WebDevServer(self.path).start()

    def broker(self):
        BrokerServer().start()

    def builder(self):
        Builder(self.path).start()

    def handle(self, args):
        self.path = args.path

        broker_proc = Process(target=self.broker)
        broker_proc.start()

        self.wait_for_broker()

        builder_proc = None
        web_proc = None
        web_dev_proc = None
        openscad_proc = None

        if args.openscad:
            openscad_proc = Process(target=self.openscad)

        if not args.openscad or args.web or args.web_dev or args.debug_web:
            self.web_dev = args.web_dev
            if args.web_dev:
                web_dev_proc = Process(target=self.web_dev_server)
                web_dev_proc.start()

            if args.debug_web:
                return self.web()

            web_proc = Process(target=self.web)
            web_proc.start()

        if args.debug_builder:
            return self.builder()

        while True:
            if web_proc and builder_proc:
                logger.info('Restarting WEB')
                web_proc.terminate()
                web_proc.join()
                web_proc = Process(target=self.web)
                web_proc.start()

            builder_proc = Process(target=self.builder)
            builder_proc.start()

            try:
                builder_proc.join()
            except KeyboardInterrupt:
                sys.exit(0)

        print(f"Exiting...")

    def wait_for_broker(self):
        def is_port_open():
            """Check if a port is open on a given host."""
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex((BROKER_HOST, BROKER_PORT)) == 0
        while not is_port_open():
            logger.info('port closed')
            time.sleep(0.1)
        logger.info(f'Broker is ready and listening on port {BROKER_PORT}')
