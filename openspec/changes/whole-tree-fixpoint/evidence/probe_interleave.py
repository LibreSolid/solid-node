"""Where the walk READS a body's motion, relative to where it BINDS it.

A relation that binds a coordinate after the walk has already composed
that body's geometry is a pose nobody sees. This measures, for a root
with two subtrees, the exact interleaving of simulate phases and
`assemble()` calls -- which is what decides whether a deferred relation
may be solved lazily or has to be solved before the walk reads anything.

Run from the worktree with PYTHONPATH=.
"""
from solid2 import cube

from solid_node.node import AssemblyNode, Solid2Node
from solid_node.motion.joints import Revolute
from solid_node.node import assembly as _assembly
from solid_node.node import base as _base

LOG = []


def patch():
    original_solve = _assembly.solve_relations
    original_assemble = _base.AbstractBaseNode.assemble

    def solve(node):
        LOG.append(f'phase   {node.name or type(node).__name__}')
        return original_solve(node)

    def assemble(self, root=None):
        LOG.append(f'  geometry read of {self.name or type(self).__name__}')
        result = original_assemble(self, root)
        LOG.append(f'  operations applied to '
                   f'{self.name or type(self).__name__}')
        return result

    _assembly.solve_relations = solve
    _base.AbstractBaseNode.assemble = assemble


patch()


class Strut(Solid2Node):
    swing = Revolute(axis=(1, 0, 0), unit='deg')

    def render(self):
        return cube([2, 2, 2])


class Body(AssemblyNode):
    """The FIRST subtree: holds the body a root relation would drive."""

    lower_strut = Strut()

    def render(self):
        return [self.lower_strut]


class Axis(AssemblyNode):
    """The SECOND subtree: holds the coordinate that relation reads."""

    column = Strut()

    def render(self):
        return [self.column]

    def simulate(self):
        self.column.swing = 12.0


class Microscope(AssemblyNode):
    body = Body()
    z_axis = Axis()

    def render(self):
        return [self.body, self.z_axis]


scope = Microscope()
scope.set_state(time=0.0)
LOG.clear()
scope.assemble()
for line in LOG:
    print(line)
