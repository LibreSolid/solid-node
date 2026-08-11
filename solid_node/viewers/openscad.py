# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""OpenSCAD-backed PNG rendering."""

import logging
import os
import shutil
import sys
import errno
from subprocess import Popen

from solid_node.core import load_node


logger = logging.getLogger('viewers.openscad')
OPENSCAD_PID = ".openscad.pid"


class OpenScadViewer:
    """Shows the rendered project in OpenSCAD."""

    def __init__(self, path):
        self.pid_file = OPENSCAD_PID
        self.path = path
        self.node = load_node(path)
        self.proc = None

    @property
    def pid(self):
        if self.proc:
            return self.proc.pid
        else:
            try:
                with open(self.pid_file) as pid_file:
                    return int(pid_file.read())
            except (FileNotFoundError, TypeError, ValueError):
                return None

    @property
    def running(self):
        pid = self.pid
        if not pid:
            return
        try:
            os.kill(pid, 0)
        except OSError as err:
            if err.errno == errno.ESRCH:
                # PID does not exist
                return False
            elif err.errno == errno.EPERM:
                # no permission to send a signal to process
                return True
            else:
                raise
        else:
            return True

    def start(self):
        if self.running:
            return
        self.proc = Popen(['openscad', self.node.scad_file])
        with open(self.pid_file, 'w') as pid_file:
            pid_file.write(f'{self.proc.pid}')

    def quit(self):
        pid = self.pid
        if pid:
            os.kill(pid, 15)
        try:
            os.remove(self.pid_file)
        except FileNotFoundError:
            pass


class OpenScadRenderer:
    def render(self, node, args, output, runner):
        command = self.wrap_command(self.build_command(node, args, output))
        logger.info('Rendering %s to %s', node.scad_file, output)
        logger.debug('OpenSCAD command: %s', ' '.join(command))
        result = runner(command, check=True, capture_output=True, text=True)
        if result.stdout:
            logger.debug(result.stdout)

    def build_command(self, node, args, output):
        command = ['openscad', '-o', output]
        if args.camera:
            command.extend(['--camera', args.camera])
        if args.autocenter:
            command.append('--autocenter')
        if args.viewall:
            command.append('--viewall')
        command.extend(['--imgsize', args.imgsize.lower().replace('x', ',')])

        projection = args.projection or 'perspective'
        command.extend(['--projection', 'o' if projection == 'ortho' else 'p'])
        command.extend(['--colorscheme', args.colorscheme or 'Cornfield'])
        if args.preview:
            command.append('--preview')
        if args.view:
            command.extend(['--view', args.view])
        command.append(node.scad_file)
        return command

    def wrap_command(self, command):
        if os.environ.get('DISPLAY'):
            return command
        xvfb_run = self.find_xvfb_run()
        if not xvfb_run:
            sys.stderr.write(
                "Error: no DISPLAY and 'xvfb-run' not found on PATH. "
                "Install xvfb (e.g. `apt-get install -y xvfb`) or run this "
                "command under `xvfb-run -a`.\n"
            )
            raise SystemExit(1)
        return [xvfb_run, '-a'] + command

    def find_xvfb_run(self):
        return shutil.which('xvfb-run')
