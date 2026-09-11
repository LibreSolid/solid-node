# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import sys
import logging
from subprocess import Popen
from solid_node.core.builder import Builder, BuildOutcome, get_build_dir
from solid_node.core.loader import ProjectManifestError, select_model
from solid_node.core.processes import Process
from solid_node.viewers.bundle import (
    INSTALL_REMEDY, has_bundle, viewer_command,
)


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


def run_builder(path, overrides, is_reload=False, callback=None,
                scad_output=False):
    Builder(
        path,
        is_reload=is_reload,
        callback=callback,
        lifecycle=True,
        overrides=overrides,
        scad_output=scad_output,
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
    and runs the browser viewer from the solid-node-viewer package unless the
    viewerless watch loop was explicitly requested.
    """

    needs_node = True

    def add_arguments(self, parser):
        self.parser = parser
        parser.add_argument('--web', action='store_true',
                            help='View the project in the browser through the installed '
                                 'solid-node-viewer (the default)')
        parser.add_argument('--web-dev', action='store_true',
                            help='Browser viewer with its own npm dev server proxied in, '
                                 'for working on the viewer itself')
        parser.add_argument('--no-web', action='store_true',
                            help='Run the builder watch loop with no viewer, for a host '
                                 'that publishes its own view of the build directory')
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
        if callback and self.web_dev:
            self.parser.error(
                '--callback is not available with --web-dev')

        # Interactive development has one viewer. Resolve it before starting
        # either child so a missing optional package never leaves a watch loop
        # running without the requested surface. `--no-web` deliberately
        # bypasses discovery for an external host or a builder-only session.
        run_web = not no_web
        if run_web and not has_bundle():
            sys.stderr.write(f'Error: {INSTALL_REMEDY}\n')
            raise SystemExit(1)

        builder_proc = None
        web_proc = None

        if run_web:
            web_proc = self.web()

        if args.debug_builder:
            return run_builder(self.path, self.overrides, callback=callback,
                               scad_output=False)

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
                                             not first_run, callback,
                                             False))
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
                    if web_proc is not None:
                        web_proc.terminate()
                        web_proc.wait()
                    sys.exit(exitcode)
                first_run = False
