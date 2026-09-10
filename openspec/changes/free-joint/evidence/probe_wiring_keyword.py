"""Probe (run from the worktree with PYTHONPATH="$PWD"): what today's
tree does with a wiring keyword that is not a Python identifier.

Evidence for a REFUSAL, not for a feature. It shows that Python does
accept a non-identifier string as a `**` key and that it reaches
`ChildDeclaration._check_wiring` intact -- so a dotted wiring keyword
COULD be made to work, and the change `free-joint` deliberately does
not: a coordinate of a joint owning several is reached by assignment
on the instance, by relation path, and by a driver or an expression,
never by a wiring keyword. Today's refusal here is incidental (the
child declares no such name); the change makes it explicit.
"""
from solid2 import cube
from solid_node.motion.joints import Revolute
from solid_node.motion.ports import RotationalPort, declared_ports
from solid_node.node import AssemblyNode, Solid2Node


class Wheel(Solid2Node):
    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cube(2, center=True)


class Rig(AssemblyNode):
    drive = RotationalPort(unit='deg')
    wheel = Wheel(**{'turn': drive})

    def render(self):
        pass

print('wiring recorded:', Rig.__dict__['wheel'].wiring)

try:
    class Bad(AssemblyNode):
        drive = RotationalPort(unit='deg')
        wheel = Wheel(**{'turn.roll': drive})

        def render(self):
            pass
except Exception as failure:
    print('dotted wiring keyword:', type(failure).__name__, failure)
else:
    print('dotted wiring keyword ACCEPTED:', Bad.__dict__['wheel'].wiring)
