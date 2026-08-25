"""Stand-in Metamaquina2 X axis for the ADR-056 spike. NON-SHIPPING.

Geometry fidelity is out of scope (spike/SCOPE.md): the axis exists to
move and be asserted against. Static placement is baked into leaf
geometry; the only operations applied at assembly level are the driven
ones, so the operation lists exercise exactly the per-tick sweep.

Layout (mm): motor mount x in [-30,-2]; two rods along X from 0 to 240
at y=+-15, z=20; carriage (left edge at x) rides above the rods with
1.5 mm clearance; pulley spins in place on the world Z axis above the
mount. At x=0 the carriage clears the mount by 2 mm — overshoot past
-2 mm interferes, which is what gives the scenario assertion teeth.

The spike's local harness (steplab.py) is gone: drivers, instructions
and the stepping loop are the shipped solid_node.simulation package,
and the port is the shipped TranslationalPort. What the spike declared
in driver-native microsteps is declared in millimetres here — the
design units a maker thinks in — which is the seam FINDINGS.md #4
named and this package closes.
"""

from solid2 import cube, cylinder, rotate, translate

from solid_node.node import AssemblyNode, Solid2Node, TranslationalPort
from solid_node.simulation import Driver, Instruction

# GT2 belt on a 20-tooth pulley: 40 mm/rev; 200 full steps x 16 microsteps.
USTEPS_PER_REV = 200 * 16
MM_PER_REV = 40.0
MM_PER_USTEP = MM_PER_REV / USTEPS_PER_REV      # 0.0125 mm
HOME_USTEPS = 8000                              # x = 100 mm


class MotorMount(Solid2Node):
    color = '#556677'

    def render(self):
        return translate([-30, -30, 0])(cube([28, 60, 50]))


class Rod(Solid2Node):
    def __init__(self, y, **kwargs):
        self.y = y
        super().__init__(y, **kwargs)

    def render(self):
        return translate([0, self.y, 20])(
            rotate([0, 90, 0])(cylinder(r=4, h=240)))


class Carriage(Solid2Node):
    color = '#aa4444'

    def render(self):
        return translate([0, -35, 25.5])(cube([40, 70, 15]))


class Pulley(Solid2Node):
    fn = 32

    def render(self):
        return translate([0, 0, 52])(cylinder(r=8, h=8))


class XAxis(AssemblyNode):
    motor = Driver(default=HOME_USTEPS, unit='ustep', dtype=int,
                   scale=MM_PER_USTEP)
    x_out = TranslationalPort(unit='mm', scale=MM_PER_USTEP)

    instructions = {
        'Home X': Instruction({'motor': 0.0}, duration=2.0),
        'Crash X': Instruction({'motor': -5.0}, duration=2.0),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mount = MotorMount()
        self.rod_front = Rod(-15)
        self.rod_back = Rod(15)
        self.carriage = Carriage()
        self.pulley = Pulley()

    def render(self):
        usteps = self.state['motor']
        # Port binding, re-executed every tick: stepper microsteps in,
        # carriage position out through the belt ratio the port
        # declares.
        self.connect(usteps, self.x_out)
        self.pulley.rotate(usteps * 360.0 / USTEPS_PER_REV, [0, 0, 1])
        self.carriage.translate([self.x_out.value, 0, 0])
        return [self.mount, self.rod_front, self.rod_back,
                self.carriage, self.pulley]
