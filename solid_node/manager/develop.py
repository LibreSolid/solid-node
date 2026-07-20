# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import sys
import logging
from multiprocessing import Process
from solid_node.core.builder import Builder, BuildOutcome, BuildSession
from solid_node.viewers.openscad import OpenScadViewer
from solid_node.viewers.web import WebViewer, WebDevServer


logger = logging.getLogger('manager.develop')


class Develop:
    """Runs all processes required for developing with solid-node.
    Monitors filesystem and executes transpilations and compilations on background,
    and runs servers to support a web frontend
    """

    needs_node = True

    def add_arguments(self, parser):
        self.parser = parser
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
        parser.add_argument('--callback', metavar='URL',
                            help='POST URL notified after each complete build')


    def openscad(self):
        OpenScadViewer(self.path).start()

    def web(self):
        WebViewer(self.path, self.web_dev).start()

    def web_dev_server(self):
        WebDevServer(self.path).start()

    def builder(self, is_reload=False, build_dir=None, callback=None):
        Builder(
            self.path,
            is_reload=is_reload,
            build_dir=build_dir,
            published_build_dir=self.build_session.build_dir,
            callback=callback,
            lifecycle=True,
        ).start()

    def handle(self, args):
        self.path = args.path
        callback = getattr(args, 'callback', None)
        if callback and (args.openscad or args.web_dev):
            self.parser.error('--callback is available only in normal web mode')

        builder_proc = None
        web_proc = None
        web_dev_proc = None
        openscad_proc = None

        if args.openscad:
            openscad_proc = Process(target=self.openscad)
            openscad_proc.start()

        if not args.openscad or args.web or args.web_dev or args.debug_web:
            self.web_dev = args.web_dev
            if args.web_dev:
                web_dev_proc = Process(target=self.web_dev_server)
                web_dev_proc.start()

            if args.debug_web:
                return self.web()

            web_proc = Process(target=self.web)
            web_proc.start()

        self.build_session = BuildSession()

        if args.debug_builder:
            try:
                return self.builder(build_dir=self.build_session.staging_dir,
                                    callback=callback)
            finally:
                self.build_session.discard()

        # Only the very first builder attempt is "startup": a project
        # that is already broken at launch exits cleanly instead of
        # looping. Every attempt after that is a WATCH-LOOP reload,
        # which must survive an import error raised while re-loading
        # edited source (see Builder.is_reload / _on_reload_exception).
        first_run = True

        try:
            while True:
                if web_proc and builder_proc:
                    logger.info('Restarting WEB')
                    web_proc.terminate()
                    web_proc.join()
                    web_proc = Process(target=self.web)
                    web_proc.start()

                builder_proc = Process(
                    target=self.builder,
                    args=(not first_run, self.build_session.staging_dir, callback),
                )
                builder_proc.start()

                try:
                    builder_proc.join()
                except KeyboardInterrupt:
                    sys.exit(0)

                exitcode = builder_proc.exitcode
                if exitcode == BuildOutcome.RENDERED.value:
                    first_run = False
                    continue
                if exitcode == BuildOutcome.SOURCE_CHANGED.value:
                    self.build_session.reset()
                    first_run = False
                    continue
                if first_run and exitcode:
                    logger.error('Initial build failed, exiting')
                    for proc in (openscad_proc, web_dev_proc, web_proc):
                        if proc is not None:
                            proc.terminate()
                            proc.join()
                    sys.exit(exitcode)
                first_run = False
        finally:
            self.build_session.discard()
