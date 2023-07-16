from math import pi

from solid2 import cube, cylinder, difference, get_animation_time, union, OpenSCADObject

from solid_node.node import Solid2Node


class ComplexObject(Solid2Node):
    """
    This is a complex object that is made up of multiple parts. The original
    example and the explanation of how to create it can be found here:
    https://www.youtube.com/watch?v=kZN_HCtXwLU

    The resulting gears can be animated by changing the FPS and the number of
    steps in the OpenSCAD view. Click on "View" -> "Animate" and change the
    values in the bar that appears at the bottom of the screen.
    """

    def render(self) -> OpenSCADObject:
        co_radius = 25
        co_height = 15

        tooth_quantity = 36
        tooth_tickness = 2 * pi * co_radius / tooth_quantity / 2

        piece = difference()(
            union()(
                cylinder(r=co_radius, h=co_height, center=True),
                [
                    (
                        cube([tooth_tickness, tooth_tickness, co_height], center=True)
                        .translate([co_radius, 0, 0])
                        .rotate([0, 0, r * 360 / tooth_quantity])
                    )
                    for r in range(0, tooth_quantity)
                ],
            ),
            union()(
                [
                    (
                        cube([3, 3, co_height * 1.1], center=True)
                        .rotate([0, 0, r * 360 / 3])
                    )
                    for r in range(0, 3)
                ]
            ),
        )

        return piece.rotate([0, 0, -get_animation_time() * 360]) + (
            piece.rotate([0, 0, get_animation_time() * 360])
            .translate([0, co_radius * 2.05, 0])
            .rotate([0, 0, 15])
        )
