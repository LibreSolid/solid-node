# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import sys
import logging
from subprocess import Popen
from solid_node.core.builder import Builder, BuildOutcome, get_build_dir
from solid_node.core.loader import ProjectManifestError, select_model
from solid_node.core.processes import Process
from solid_node.viewers.openscad import OpenScadViewer
from solid_node.viewers.bundle import (
    INSTALL_REMEDY, has_bundle, viewer_command,
)
from solid_node.openscad import OpenScadUnavailable, require_openscad


logger = logging.getLogger('manager.develop')


# Every subprocess target is a module-level function taking plain values.
# The subprocesses a develop session runs do not inherit this process's
# memory; each is handed its target and arguments to reconstruct in a fresh
# interpreter, and the command object -- which holds an unpicklable
# ArgumentParser -- stays here. See `solid_node.core.processes`.
#
# The browser viewer is not one of these targets at all: it is another
# package's program, `solid-node-viewer serve`, started with Popen on the
# project's build directory.

def run_openscad_viewer(path, overrides):
    OpenScadViewer(path, overrides=overrides).start()


def run_builder(path, overrides, is_reload=False, callback=None):
    Builder(
        path,
        is_reload=is_reload,
        callback=callback,
        lifecycle=True,
        overrides=overrides,
    ).start()


def web_viewer_command(path, web_dev=False):
    """The viewer's server, on this project's build directory.

    The server is another package's process: it is handed the directory
    and nothing else, and it reads its ports from the same environment
    this command loaded `.env` into.
    """
    command = viewer_command() + ['serve', '--build-dir', get_build_dir(path)]
    if web_dev:
        command.append('--start-frontend')
    return command


class Develop:
    """Runs all processes required for developing with solid-node.
    Monitors filesystem and executes transpilations and compilations on background,
    and runs a viewer: the browser viewer of the solid-node-viewer package when
    it is installed, the OpenSCAD GUI otherwise.
    """

    needs_node = True

    def add_arguments(self, parser):
        self.parser = parser
        parser.add_argument('--web', action='store_true',
                            help='View the project in the browser through the installed '
                                 'solid-node-viewer (the default when it is installed)')
        parser.add_argument('--web-dev', action='store_true',
                            help='Browser viewer with its own npm dev server proxied in, '
                                 'for working on the viewer itself')
        parser.add_argument('--no-web', action='store_true',
                            help='Run the builder watch loop with no viewer, for a host '
                                 'that publishes its own view of the build directory')
        parser.add_argument('--openscad', action='store_true',
                            help='Show project in OpenSCAD (the default when '
                                 'solid-node-viewer is not installed)')
        parser.add_argument('--debug-builder', action='store_true',
                            help='Debug mode supports breakpoints, but reload is not automatic')
        parser.add_argument('--callback', metavar='URL',
                            help='POST URL notified after each complete build')

    def web(self):
        return Popen(web_viewer_command(self.path, self.web_dev))

    def handle(self, args):
        # A declared model name, or the default, selects what to load and
        # the build directory to serve; the builders this loop starts and
        # the viewer it serves inherit that selection.
        try:
            selection = select_model(args.path)
        except ProjectManifestError as error:
            sys.stderr.write(f'Error: {error}\n')
            raise SystemExit(1)
        selection.anchor()
        self.path = selection.reference
        # Every builder this loop starts, first run and each reload,
        # loads the root with the same parameters the session asked for.
        self.overrides = list(getattr(args, 'set', None) or [])
        callback = getattr(args, 'callback', None)
        no_web = getattr(args, 'no_web', False)
        self.web_dev = getattr(args, 'web_dev', False)
        wants_web = args.web or self.web_dev

        if no_web and wants_web:
            self.parser.error(
                '--no-web cannot be combined with --web or --web-dev')
        if callback and (args.openscad or self.web_dev):
            self.parser.error(
                '--callback is not available with --openscad or --web-dev')

        # Which viewer opens. An explicit flag is honoured or refused, never
        # substituted. With no flag, the browser viewer runs when its package
        # is installed and the OpenSCAD GUI runs otherwise -- a workbench
        # choice with nothing downstream of it, unlike a snapshot's renderer.
        viewer_installed = has_bundle()
        if no_web:
            run_web = run_openscad = False
        elif wants_web or args.openscad:
            run_web = wants_web
            run_openscad = args.openscad
            if run_web and not viewer_installed:
                sys.stderr.write(f'Error: {INSTALL_REMEDY}\n')
                raise SystemExit(1)
        else:
            run_web = viewer_installed
            run_openscad = not viewer_installed

        if run_openscad:
            try:
                require_openscad(
                    'the requested OpenSCAD viewer',
                    'opening that viewer launches OpenSCAD')
            except OpenScadUnavailable as error:
                if args.openscad:
                    sys.stderr.write(f'Error: {error}\n')
                else:
                    sys.stderr.write(
                        f'Error: nothing can show this project. {INSTALL_REMEDY} '
                        f'-- or install OpenSCAD for the GUI viewer: {error}\n')
                raise SystemExit(1)

        builder_proc = None
        web_proc = None
        openscad_proc = None

        if run_openscad:
            openscad_proc = Process(target=run_openscad_viewer,
                                    args=(self.path, self.overrides))
            openscad_proc.start()

        if run_web:
            web_proc = self.web()

        if args.debug_builder:
            return run_builder(self.path, self.overrides, callback=callback)

        # Only the very first builder attempt is "startup": a project
        # that is already broken at launch exits cleanly instead of
        # looping. Every attempt after that is a WATCH-LOOP reload,
        # which must survive an import error raised while re-loading
        # edited source (see Builder.is_reload / _on_reload_exception).
        first_run = True

        while True:
                if web_proc and builder_proc:
                    # The server greets a reconnecting browser with `reload`,
                    # so restarting it is how a completed build reaches the page.
                    logger.info('Restarting WEB')
                    web_proc.terminate()
                    web_proc.wait()
                    web_proc = self.web()

                builder_proc = Process(target=run_builder,
                                       args=(self.path, self.overrides,
                                             not first_run, callback))
                builder_proc.start()

                try:
                    builder_proc.join()
                except KeyboardInterrupt:
                    if web_proc is not None:
                        web_proc.terminate()
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
                    if openscad_proc is not None:
                        openscad_proc.terminate()
                        openscad_proc.join()
                    if web_proc is not None:
                        web_proc.terminate()
                        web_proc.wait()
                    sys.exit(exitcode)
                first_run = False
