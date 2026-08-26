# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Stepped simulation: drivers, instructions, and the fixed-dt loop.

A machine that is not periodic -- a printer executing instructions, a
car with independent steering and throttle -- cannot be written as a
function of ADR-008's single looping scalar. This package is the layer
that produces the driver snapshots the node layer already knows how to
bind: state advances here, in exactly one place, and geometry stays a
pure function of the snapshot.

The dependency runs one way. solid_node.node never imports this
package; a project declares Drivers as class attributes and the
simulation discovers them off the class -- across the whole linked
tree, by qualified id (`enumeration.qualified_drivers`) -- so a node
without drivers carries no simulation import anywhere.
"""

from .driver import Driver, RampProgram
from .enumeration import qualified_drivers, qualified_instructions
from .instruction import Instruction
from .scenario import ScenarioTest
from .sim import Sim

__all__ = ['Driver', 'Instruction', 'RampProgram', 'ScenarioTest', 'Sim',
           'qualified_drivers', 'qualified_instructions']
