"""What a tuple end does on this tree TODAY, and why the source-side
sentence cannot be spelled with a tuple.

Run from the worktree with PYTHONPATH="$PWD".
"""
import sys

from solid_node.motion.couplings import Affine
from solid_node.motion.joints import Revolute
from solid_node.motion.ports import RotationalPort, SignalPort
from solid_node.node import AssemblyNode

print('solid_node:', __import__('solid_node').__file__)


def show(label, thunk):
    try:
        value = thunk()
    except Exception as failure:          # noqa: BLE001 - the point
        print(f'{label}: {type(failure).__name__}: {failure}')
    else:
        print(f'{label}: OK -> {value!r}')


class Leaf(AssemblyNode):
    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        pass


# 1. A tuple display has no `drives`, and cannot be given one.
def tuple_source():
    class Root(AssemblyNode):
        a = SignalPort()
        b = SignalPort()
        child = Leaf()
        (a, b).drives(child.turn, law=lambda *n: (lambda x, y: x + y))

        def render(self):
            pass
    return Root


show('(a, b).drives(...)', tuple_source)
print('tuple has drives:', hasattr((1, 2), 'drives'))
try:
    tuple.drives = lambda *a, **k: None
except Exception as failure:              # noqa: BLE001
    print('patching tuple:', type(failure).__name__, failure)


# 2. A tuple as the DRIVEN argument is syntactically fine and reaches the
#    framework, which refuses it as "not a coordinate".
def tuple_driven():
    class Root(AssemblyNode):
        a = SignalPort()
        one = Leaf()
        two = Leaf()
        a.drives((one.turn, two.turn), law=lambda *n: (lambda x: (x, x)))

        def render(self):
            pass
    return Root


show('a.drives((b, c), law=...)', tuple_driven)


# 3. `&` between two coordinate declarations today.
def ampersand():
    class Root(AssemblyNode):
        a = SignalPort()
        b = SignalPort()

        def render(self):
            pass
    return Root


def ampersand_refusal():
    class Root(AssemblyNode):
        a = SignalPort()
        b = SignalPort()
        child = Leaf()
        (a & b).drives(child.turn, law=lambda *n: (lambda x, y: x + y))

        def render(self):
            pass
    return Root


show('(a & b).drives(...)', ampersand_refusal)


# 4. A class body that binds the name `drives` shadows any free function
#    of that name -- InMoov's Hand does exactly this
#    (Inmoov_sim/hand.py:213, `drives = Drive().repeat(5)`).
def drives(*args, **kwargs):
    return 'the free function'


class Hand:
    drives = ['a', 'b', 'c', 'd', 'e']     # the five drive units
    try:
        result = drives(('thumb', 'index'), 'fingers.drive')
    except Exception as failure:           # noqa: BLE001
        result = f'{type(failure).__name__}: {failure}'


print('a free `drives` inside a body that declares one:', Hand.result)


# 5. What the law is handed today, and what its forward face is called
#    with.
seen = []


def law(driver, driven):
    seen.append(('law called with', type(driver).__name__,
                 type(driven).__name__))
    return Affine(2.0)


class OneToOne(AssemblyNode):
    a = SignalPort()
    child = Leaf()
    a.drives(child.turn, law=law)

    def render(self):
        pass

    def simulate(self):
        self.a = 3.0


node = OneToOne()
print('law calls at realization:', seen)


# 6. `&` is free on EVERY declaration that carries `drives`, and a
#    special method is looked up on the type, so no `__getattr__` of a
#    declaration can intercept it.
from solid_node.simulation import Driver                      # noqa: E402


class Pairs(AssemblyNode):
    port = SignalPort()
    driver = Driver(default=0.0)
    child = Leaf()
    joint = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        pass


kinds = {
    'port': Pairs.__dict__['port'],
    'driver': Pairs.__dict__['driver'],
    'child declaration': Pairs.__dict__['child'],
    'joint': Pairs.__dict__['joint'],
    'path reference': Pairs.__dict__['child'].turn,
}
for name, left in kinds.items():
    for other, right in kinds.items():
        try:
            left & right
        except TypeError as failure:
            outcome = f'TypeError: {failure}'
        except Exception as failure:                          # noqa: BLE001
            outcome = f'{type(failure).__name__}: {failure}'
        else:
            outcome = 'NO REFUSAL -- something already defines &'
        if 'unsupported operand' not in outcome:
            print(f'{name} & {other}: {outcome}')
print('& is unused on every declaration kind that carries drives: '
      'nothing printed above')
