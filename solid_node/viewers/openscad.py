# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import errno
from subprocess import Popen
from solid_node.core import load_node

OPENSCAD_PID = ".openscad.pid"


class OpenScadViewer:
    """Shows the rendered project in OpenScad."""

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
                return int(open(self.pid_file).read())
            except (FileNotFoundError, TypeError):
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
        open(self.pid_file, 'w').write(f'{self.proc.pid}')

    def quit(self):
        pid = self.pid
        if pid:
            os.kill(pid, 15)
        try:
            os.remove(self.pid_file)
        except FileNotFoundError:
            pass
