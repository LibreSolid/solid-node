"""Two-axis stand-in machine for the ADR-056 expression spike. NON-SHIPPING.

The first spike's X axis (spike/axis/axis_model.py), duplicated: ONE
class declaring `motor`, instantiated twice as `x_axis` and `y_axis`
under a parent assembly, so the class-local driver name collides for
real instead of by construction (spike/expressions/SCOPE.md, model).

Geometry fidelity remains out of scope. What the render() below is
built to exercise is the shape of the EXPRESSIONS, not the mechanism:

- a LINEAR driver expression (pulley angle from microsteps),
- a driver expression through a PORT and its unit scale (carriage),
- a NON-LINEAR degree-trig expression of a driver-derived angle
  (the cover tilt), which is exactly the ADR-022 class that
  `solid_node.math` exists for, and
- a MIXED expression containing BOTH `$t` and a driver term (the
  cover shift), which sub-question 4 must survive partial
  substitution.

`label` is a constructor argument only so the two axes get distinct
uniq_ids; a node's artifact key is class + constructor parameters, so
without it both instances would write one another's Axis-level .scad.
"""

from solid2 import cube, cylinder, rotate, translate

import solid_node.math as sn_math
from solid_node.node import AssemblyNode, Solid2Node, TranslationalPort
from solid_node.simulation import Driver, Instruction

# GT2 belt on a 20-tooth pulley: 40 mm/rev; 200 full steps x 16 microsteps.
USTEPS_PER_REV = 200 * 16
MM_PER_REV = 40.0
MM_PER_USTEP = MM_PER_REV / USTEPS_PER_REV      # 0.0125 mm
DEG_PER_USTEP = 360.0 / USTEPS_PER_REV          # 0.1125 deg
HOME_USTEPS = 8000                              # 100 mm


class Rail(Solid2Node):
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


class Cover(Solid2Node):
    color = '#557799'

    def render(self):
        return translate([0, -40, 45])(cube([200, 4, 20]))


class Axis(AssemblyNode):
    """One driven linear axis. Declares the class-local driver `motor`."""

    motor = Driver(default=HOME_USTEPS, unit='ustep', dtype=int,
                   scale=MM_PER_USTEP)
    position = TranslationalPort(unit='mm', scale=MM_PER_USTEP)

    instructions = {
        'Home': Instruction({'motor': 0.0}, duration=2.0),
    }

    def __init__(self, label, **kwargs):
        super().__init__(label, **kwargs)
        self.label = label
        self.rail_front = Rail(-15)
        self.rail_back = Rail(15)
        self.carriage = Carriage()
        self.pulley = Pulley()
        self.cover = Cover()

    def render(self):
        usteps = self.state['motor']

        # Port binding, re-executed every render: microsteps in,
        # carriage position out through the belt ratio.
        self.connect(usteps, self.position)

        # 1. linear in the driver
        angle = usteps * DEG_PER_USTEP
        self.pulley.rotate(angle, [0, 0, 1])

        # 2. through the port's unit scale
        self.carriage.translate([self.position.value, 0, 0])

        # 3. non-linear degree trig of a driver-derived angle: the
        #    ADR-022 class. Numerically this is a real float under a
        #    bound driver; symbolically it is an OpenSCAD call string.
        self.cover.rotate(sn_math.asin(0.25 * sn_math.sin(angle)), [1, 0, 0])

        # 4. MIXED: one formula containing both $t and a driver term.
        self.cover.translate([
            5.0 * sn_math.cos(360.0 * self.time) + self.position.value * 0.1,
            0,
            0,
        ])

        # 5. a POWER term. solid2 and OpenSCAD spell exponentiation
        #    `^`, which jokenizer parses as JavaScript bitwise XOR
        #    unless the evaluator rewrites it -- the other half of
        #    ADR-022's parity story, and worth putting on the wire.
        lift = sn_math.sqrt(400.0 - (0.01 * angle) ** 2)
        self.pulley.translate([0, 0, lift * 0.1])

        return [self.rail_front, self.rail_back, self.carriage,
                self.pulley, self.cover]


class Machine(AssemblyNode):
    """The parent assembly. Declares NO driver of its own on purpose:
    every driver in this machine is class-local to a duplicated child,
    which is the situation sub-questions 2 and 5 are about."""

    # Overridable so the runner can substitute an instrumented Axis
    # subclass when it probes WHEN a node learns its path.
    axis_class = Axis

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x_axis = self.axis_class('x')
        self.y_axis = self.axis_class('y')
        # Static placement, applied outside any render() so the
        # _idempotent_render sweep never touches it (base.py
        # _tag_animator: an operation applied with an empty render
        # stack is left untagged).
        self.y_axis.rotate(90, [0, 0, 1])
        self.y_axis.translate([0, 0, 60])

    def render(self):
        return [self.x_axis, self.y_axis]
