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
import re
import tempfile
from subprocess import Popen
from solid2 import scad_render
from solid_node.node.leaf import LeafNode


class Solid2Node(LeafNode):
    """
    Represents a 3D object created using the SolidPython2 tool.
    """

    namespace = 'solid2'

    def as_scad(self, rendered):
        """Doesn't do anything, as solid2 objects are already OpenScad objects"""
        return rendered

    def as_number(self, n):
        """Receives a solid2 function result and calculates its number.
        uses an openscad process internally to do the calculation."""
        if type(n).__module__.startswith('solid2'):
            # This is very clumsy, but it works. Trimesh cannot load
            # translated / rotated mesh, and transforming meshes after loading
            # requires knowing the final number in python memory.
            # If it's a scad function, then we need to get from OpenScad.

            lines = scad_render(n).split('\n')
            code = []
            while lines[0].startswith('include'):
                code.append(lines.pop(0))
            while not lines[0].strip():
                lines.pop(0)
            code.append('echo(')
            while lines:
                line = lines.pop(0)
                if line.strip():
                    code.append(line)
            code = '\n'.join(code)
            code = re.sub(r";$", ");", code)

            scad_file = tempfile.mktemp(suffix='.scad')
            result_file = tempfile.mktemp('.echo')

            try:
                open(scad_file, 'w').write(code)
                proc = Popen(['openscad', '-o', result_file, scad_file])
                proc.wait()
                result = open(result_file).read()
                result = result.replace('ECHO: ', '').strip()
                n = int(result)
            finally:
                os.remove(scad_file)
                os.remove(result_file)

        return n
