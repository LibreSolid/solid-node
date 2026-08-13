# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import sys
import logging
from multiprocessing import Process
from solid_node.core.builder import Builder, BuildOutcome
from solid_node.viewers.openscad import OpenScadViewer
from solid_node.viewers.web import WebViewer, WebDevServer
from solid_node.openscad import OpenScadUnavailable, require_openscad


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
        parser.add_argument('--no-web', action='store_true',
                            help='Run the builder watch loop with no web viewer, for a host '
                                 'that publishes its own view of the build directory')
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
            callback=callback,
            lifecycle=True,
        ).start()

    def handle(self, args):
        self.path = args.path
        callback = getattr(args, 'callback', None)
        no_web = getattr(args, 'no_web', False)
        wants_web = args.web or args.web_dev or args.debug_web

        if no_web and wants_web:
            self.parser.error(
                '--no-web cannot be combined with --web, --web-dev or --debug-web')
        if callback and (args.openscad or args.web_dev):
            self.parser.error(
                '--callback is not available with --openscad or --web-dev')

        if args.openscad:
            try:
                require_openscad(
                    'the requested OpenSCAD viewer',
                    'opening that viewer launches OpenSCAD')
            except OpenScadUnavailable as error:
                sys.stderr.write(f'Error: {error}\n')
                raise SystemExit(1)

        builder_proc = None
        web_proc = None
        web_dev_proc = None
        openscad_proc = None

        if args.openscad:
            openscad_proc = Process(target=self.openscad)
            openscad_proc.start()

        # The web viewer runs unless something suppresses it. Two things
        # do: `--no-web` asks for the builder watch loop alone, and
        # `--openscad` on its own means the OpenSCAD GUI is the only viewer
        # wanted.
        openscad_only = args.openscad and not wants_web
        if not (no_web or openscad_only):
            self.web_dev = args.web_dev
            if args.web_dev:
                web_dev_proc = Process(target=self.web_dev_server)
                web_dev_proc.start()

            if args.debug_web:
                return self.web()

            web_proc = Process(target=self.web)
            web_proc.start()

        if args.debug_builder:
            return self.builder(callback=callback)

        # Only the very first builder attempt is "startup": a project
        # that is already broken at launch exits cleanly instead of
        # looping. Every attempt after that is a WATCH-LOOP reload,
        # which must survive an import error raised while re-loading
        # edited source (see Builder.is_reload / _on_reload_exception).
        first_run = True

        while True:
                if web_proc and builder_proc:
                    logger.info('Restarting WEB')
                    web_proc.terminate()
                    web_proc.join()
                    web_proc = Process(target=self.web)
                    web_proc.start()

                builder_proc = Process(target=self.builder,
                                       args=(not first_run, None, callback))
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
