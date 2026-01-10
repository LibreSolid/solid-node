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
import sys
import inspect
from importlib import import_module
from solid_node.node.base import AbstractBaseNode
from solid_node.test import TestCase, TestCaseMixin

sys.path.append(os.getcwd())


def load_node(path):
    if not path.endswith('.py'):
        raise Exception(f"Can only load .py files, not {path}")
    return load_instance(path, AbstractBaseNode)


def load_test(path):
    if not path.endswith('.py'):
        raise Exception(f"Can only load .py files, not {path}")

    parts = path.split('/')
    if parts[-1] == '__init__.py':
        parts[-1] = 'test.py'
    else:
        parts[-1] = f'test_{parts[-1]}'
    test_path = '/'.join(parts)
    if os.path.exists(test_path):
        return load_instance(test_path, TestCase)


def load_instance(path, BaseClass):
    path = os.path.realpath(path)
    module = import_module_from_path(path)
    klass = find_class(path, module, BaseClass)
    return klass()


def import_module_from_path(path):
    relative_path = os.path.relpath(path)
    module_name = relative_path.replace('/', '.')[:-3]
    return import_module(module_name)


def find_class(path, module, BaseClass):
    for name, klass in module.__dict__.items():
        if isinstance(klass, type) and issubclass(klass, BaseClass) \
           and inspect.getfile(klass) == path:
            return klass
