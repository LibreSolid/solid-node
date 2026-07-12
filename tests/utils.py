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

import re


def format_codes(generated, expected):
    generated = re.sub(r'//.+?\n', '', generated)
    generated = generated.strip()
    generated = generated.replace('\t', '    ').strip()
    first_line = expected.split('\n')[1]
    spaces = len(first_line) - len(first_line.strip())
    column = '\n' + ' ' * spaces

    expected = expected.replace(column, '\n').strip()

    return generated, expected
