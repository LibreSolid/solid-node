"""What actually happens, in what order, for a three-level tree.

Run from the worktree:
    PYTHONPATH=. <venv>/bin/python \
        openspec/changes/whole-tree-fixpoint/evidence/probe_order.py

Patches the four seams of the lifecycle (`_sweep`, `_rest`,
`clear_solved`, `solve_relations`) and `assemble` to print one line each,
so the ORDER of events is measured rather than read off the source.
"""
import sys

from solid2 import cube

from solid_node.node import AssemblyNode, Solid2Node
from solid_node.motion.joints import Revolute
from solid_node.motion.ports import RotationalPort
from solid_node.node import assembly as _assembly
from solid_node.node import base as _base

LOG = []


def note(text):
    LOG.append(text)


def patch():
    original_sweep = _assembly._sweep
    original_clear = _assembly.clear_solved
    original_solve = _assembly.solve_relations
    original_rest = _assembly._rest
    original_assemble = _base.AbstractBaseNode.assemble

    def sweep(node):
        note(f'  sweep      {node.__class__.__name__}')
        return original_sweep(node)

    def clear(node):
        note(f'  clear      {node.__class__.__name__}')
        return original_clear(node)

    def solve(node):
        note(f'  SOLVE      {node.__class__.__name__}')
        return original_solve(node)

    def rest(node, render):
        cached = '_rest' in node.__dict__
        note(f'  rest       {node.__class__.__name__}'
             f'{" (cached)" if cached else " (runs render)"}')
        return original_rest(node, render)

    def assemble(self, root=None):
        note(f'ASSEMBLE     {self.__class__.__name__}')
        return original_assemble(self, root)

    _assembly._sweep = sweep
    _assembly.clear_solved = clear
    _assembly.solve_relations = solve
    _assembly._rest = rest
    _base.AbstractBaseNode.assemble = assemble


patch()


class Leaf(Solid2Node):
    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cube([2, 2, 2])


class Grandchild(AssemblyNode):
    knob = RotationalPort(unit='deg')
    leaf = Leaf()
    knob.drives(leaf.turn, ratio=2)

    def render(self):
        note('  render     Grandchild')
        return [self.leaf]

    def simulate(self):
        note('  simulate   Grandchild')


class Child(AssemblyNode):
    dial = RotationalPort(unit='deg')
    grandchild = Grandchild()
    dial.drives(grandchild.knob)

    def render(self):
        note('  render     Child')
        return [self.grandchild]

    def simulate(self):
        note('  simulate   Child (binds dial)')
        self.dial = 5.0


class Root(AssemblyNode):
    child = Child()

    def render(self):
        note('  render     Root')
        return [self.child]

    def simulate(self):
        note('  simulate   Root')


def show(title):
    print(f'--- {title}')
    for line in LOG:
        print(line)
    print()
    LOG.clear()


root = Root()
show('construction (realization, resolve_declared_relations)')

root.set_state(time=0.0)
show('set_state(time=0.0)')

root.assemble()
show('assemble()')

root.set_state(time=0.5)
show('set_state(time=0.5) -- the second run')

print('leaf turn value:', root.child.grandchild.leaf.turn.value)
print('leaf operations:', root.child.grandchild.leaf.operations)
sys.exit(0)
