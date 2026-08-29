# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Top-level package for Solid Framework API."""

__author__ = """Luis Fagundes"""
__email__ = 'lhfagundes@gmail.com'
__version__ = '0.4.0'

from .base import StlRenderStart
from .assembly import AssemblyNode
from .ports import (Port, RotationalPort, TranslationalPort, SignalPort,
                    declared_ports)
from .fusion import FusionNode
from .adapters.cadquery import CadQueryNode
from .adapters.build123d import Build123dNode
from .sheet_leaf import SheetLeafNode
from .adapters.build123d_sheet import Build123dSheetNode
from .flexible import FlexibleNode
from .adapters.molejo import MolejoNode
from .adapters.solid2 import Solid2Node
from .adapters.openscad import OpenScadNode
from .adapters.jscad import JScadNode
from .adapters.stl import StlNode
from .decorators import property_as_number
