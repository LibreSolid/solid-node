"""Top-level package for Solid Framework API."""

__author__ = """Luis Fagundes"""
__email__ = 'lhfagundes@gmail.com'
__version__ = '0.1.0'

from .base import StlRenderStart
from .assembly import AssemblyNode
from .fusion import FusionNode
from .adapters.cadquery import CadQueryNode
from .adapters.solid2 import Solid2Node
from .adapters.openscad import OpenScadNode
