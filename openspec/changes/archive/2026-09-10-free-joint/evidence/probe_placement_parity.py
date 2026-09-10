"""Every joint-carrying fixture of the existing suite, posed and printed
as a composed world matrix.

Run against the BASE tree and against this implementation, and diff: the
question "did anything existing move?" is answered by the matrices, not
by "the tests pass". Nothing here is new in this cycle -- the fixtures
are the ones cycles 1 and 2 left behind.

    PYTHONPATH=<tree> python probe_placement_parity.py <out.txt>
"""
import sys

import numpy as np

from tests.test_joints import (Arm, BoredDisk, CarriedDisk, Hinge, Mixed,
                               Slider, SpunAndCarried, ThreeSub, TwoFreedom,
                               WideHinge, DISK_LIFT, ORBIT_LIFT, SPUN_LIFT,
                               THREE_LIFT, TWO_FREEDOM_LIFT)
from tests.test_joints import (Cycloidal, CycloidalSwapped, ContiguityBench,
                               BothSidesBench, OrbitContiguityBench,
                               OrbitFirstBench, PivotFirstBench,
                               SlideFirstBench, SpinFirstBench)
from solid_node.node.base import _compose_world_matrix


def show(label, node):
    matrix = np.array(_compose_world_matrix(node), dtype=float)
    print(f'--- {label}')
    for row in matrix:
        print('   ' + '  '.join(f'{value: .15e}' for value in row))
    print('    operations ' + repr([operation.serialized
                                    for operation in node.operations]))


def posed():
    body = Hinge()
    body.translate([0, 0, 3])
    body.swing = 35
    show('Hinge.swing=35', body)

    wide = WideHinge()
    wide.translate([0, 0, 3])
    wide.swing = -170
    show('WideHinge.swing=-170', wide)

    slider = Slider()
    slider.translate([2, 0, 0])
    slider.travel = 120
    slider.spin = 25
    show('Slider.travel=120,spin=25', slider)

    mixed = Mixed()
    mixed.swing = 12
    show('Mixed.swing=12', mixed)

    two = TwoFreedom()
    two.translate(TWO_FREEDOM_LIFT)
    two.pivot = 35
    two.slide = 12
    show('TwoFreedom.pivot=35,slide=12', two)

    three = ThreeSub()
    three.translate(THREE_LIFT)
    three.c = 15
    three.b = 12
    three.a = 35
    show('ThreeSub.a=35,b=12,c=15', three)

    spun = SpunAndCarried()
    spun.translate(SPUN_LIFT)
    spun.spin = 35
    spun.carry = 40
    show('SpunAndCarried.spin=35,carry=40', spun)

    carried = CarriedDisk()
    carried.translate(ORBIT_LIFT)
    carried.orbit = 17
    show('CarriedDisk.orbit=17', carried)

    bored = BoredDisk()
    bored.translate(ORBIT_LIFT)
    bored.orbit = 90
    show('BoredDisk.orbit=90', bored)

    for label, bench in (('PivotFirstBench', PivotFirstBench()),
                         ('SlideFirstBench', SlideFirstBench())):
        bench.set_state(angle=35, offset=12)
        show(f'{label}.body', bench.body)

    for label, bench in (('SpinFirstBench', SpinFirstBench()),
                         ('OrbitFirstBench', OrbitFirstBench())):
        bench.set_state(angle=35, carry=40)
        show(f'{label}.disk', bench.disk)

    for label, bench in (('Cycloidal', Cycloidal()),
                         ('CycloidalSwapped', CycloidalSwapped())):
        bench.set_state(shaft=40)
        show(f'{label}.disk', bench.disk)

    for label, bench in (('ContiguityBench', ContiguityBench()),
                         ('OrbitContiguityBench', OrbitContiguityBench())):
        bench.render()
        show(f'{label}.body', bench.body)

    both = BothSidesBench()
    both.set_state(angle=25)
    show('BothSidesBench.hinge', both.hinge)

    for angle in (0, 30, 90, -45):
        arm = Arm()
        arm.set_state(angle=angle)
        show(f'Arm.forearm.link angle={angle}', arm.forearm.link)


if __name__ == '__main__':
    stream = open(sys.argv[1], 'w') if len(sys.argv) > 1 else sys.stdout
    original = sys.stdout
    sys.stdout = stream
    try:
        posed()
    finally:
        sys.stdout = original
        if stream is not sys.stdout:
            stream.close()
