
.. _leaf-nodes:

==============
Modeling parts
==============

Make sure you have completed the :doc:`Quickstart <quickstart>`.
At this point, you should be able to view your project in the viewer
- either Openscad or the web viewer - and have a source code to edit.

In Solid Node, a project is organized in a tree structure, with leaf
nodes and internal nodes. **Leaf nodes** use underlying modelling
libraries, namely **SolidPython**, **CadQuery**, **build123d**,
**OpenScad** and **JScad**, to generate solid models — each leaf node is
one part.
**Internal nodes** combine children nodes into assemblies and fusions,
covered in :doc:`Combining parts <assemblies>`.

Each node implements the `render()` method. Leaf nodes return an object
of the underlying library.

There are five types of LeafNodes, each supporting one underlying
technology to create solids:

* **Solid2Node** Uses Solid Python 2, which is a python wrapper around OpenScad
* **CadQueryNode** Uses CadQuery, a pure python modeler based on OCCT
* **Build123dNode** Uses build123d, a pure python modeler based on OCCT
* **OpenScadNode** A wrapper around one OpenScad module
* **JScadNode** A wrapper around one JScad module

There is also one leaf kind that is not a modelling technology but a way
of making:

* **Build123dSheetNode** A part cut from sheet stock, authored as a 2D
  profile plus a thickness

The :doc:`Quickstart <quickstart>` starts with a Solid2Node example showing
a box with a hole. Below are the codes for the same model in each modelling
technology.

Solid2Node
==========

The starting structure created by `solid new` implements a **Solid2Node**
node, which uses **solidpython2** to create models. Open `myproject/myproject.py`:

.. code-block:: python

    from solid_node.node import Solid2Node
    from solid2 import cube, cylinder, translate

    class DemoProject(Solid2Node):

        def render(self):
            return translate(-25, -25, 0)(
                cube(50, 50, 50)
            ) - cylinder(r=10, h=100)

Rendered with ``solid export`` and embedded below:

.. solid-node:: _exports/demo_project
   :height: 360px

Note that `translate` here is a **solid2** primitive, applied inside the
model. Nodes also have a `translate()` method of their own, used to
position parts in assemblies — that one is covered in
:doc:`Animating with time <animation>`.

CadQueryNode
============

The same model can be obtained using **CadQuery**:

.. code-block:: python

    import cadquery as cq
    from solid_node.node import CadQueryNode

    class DemoProject(CadQueryNode):

        def render(self):
            wp = cq.Workplane("XY")
            cube = wp.box(50, 50, 50)
            hole = wp.workplane(offset=-50).circle(10).extrude(100)
            return cube.cut(hole)

The same box with a hole, this time rendered by CadQuery:

.. solid-node:: _exports/demo_cadquery
   :height: 360px

**TIP**: if you want to use CQ-editor, you can add `show_object` without
conflicting with Solid Node:

.. code-block:: python

    if __name__ == '__cq_main__':
        show_object(DemoProject().render())

Build123dNode
=============

The same model in **build123d**, which like CadQuery is a pure python
modeler over OCCT, with a different API:

.. code-block:: python

    from build123d import BuildPart, Box, Cylinder, Mode
    from solid_node.node import Build123dNode

    class DemoProject(Build123dNode):

        def render(self):
            with BuildPart() as part:
                Box(50, 50, 50)
                Cylinder(radius=10, height=100, mode=Mode.SUBTRACT)
            return part.part

And the same box with a hole, rendered by build123d:

.. solid-node:: _exports/demo_build123d
   :height: 360px

build123d offers two ways to write a model, and a node may `render()`
either. The *builder* mode above collects objects inside a context
manager; the *algebra* mode composes shapes with operators, and needs no
builder:

.. code-block:: python

    from build123d import Box, Cylinder
    from solid_node.node import Build123dNode

    class DemoProject(Build123dNode):

        def render(self):
            return Box(50, 50, 50) - Cylinder(radius=10, height=100)

Returning the builder itself rather than its `.part` also works — the
node takes the finished part — so both of these are equivalent:

.. code-block:: python

    return part.part
    return part

A leaf node is one part, so `render()` must produce a solid: a
`Part`, a `Solid`, a `Compound`, or a builder holding one. Returning a
build123d sketch or curve raises an error naming the node, rather than
failing later in the STL export.

**NOTE**: `Build123dNode` and `CadQueryNode` are both OCCT front ends
and both produce exact geometry, so they mix freely — a fusion may take
children from either, and the parts fuse exactly. Neither needs OpenScad
installed. See :doc:`Combining parts <assemblies>`.

Build123dSheetNode
==================

Some parts are not modelled, they are cut. A panel of plywood, MDF or
acrylic is a flat profile in stock of a known thickness, and what a laser
cutter needs is that profile — not a mesh of the finished part.

A **Build123dSheetNode** authors exactly that. Instead of `render()`, it
implements `profile()`, returning a build123d sketch, and declares the
`thickness` of the stock:

.. code-block:: python

    from build123d import Circle, Rectangle
    from solid_node.node import Build123dSheetNode

    class DemoProject(Build123dSheetNode):

        thickness = 6

        def profile(self):
            return Rectangle(50, 50) - Circle(10)

The same square-with-a-hole, this time as a part cut from 6 mm sheet:

.. solid-node:: _exports/demo_sheet
   :height: 360px

The node's solid is that profile extruded from the XY plane along +Z by
`thickness`, and the node derives it for you — `render()` is not an
extension point here. That is the whole point of the type: the part you
see in the viewer, the STL you test against, and the file you cut all
come from one authored profile, so they cannot drift apart. A part whose
solid and cut file were written down separately would eventually
disagree, and the cutter would faithfully cut the disagreement.

The profile contract
--------------------

A sheet part is one piece, so `profile()` must produce exactly one planar
face: a single outer boundary with any holes strictly inside it, lying on
the XY plane. Anything else raises an error naming the node and what it
produced, before any file is written — two disjoint faces (author each
piece as its own node), a solid, a curve, or a profile authored on
another plane.

`profile()` may return a `Sketch`, a bare `Face`, or the `BuildSketch`
builder itself, just as `Build123dNode` accepts a `BuildPart` or its
`.part`:

.. code-block:: python

    def profile(self):
        with BuildSketch() as sketch:
            Rectangle(50, 50)
            Circle(10, mode=Mode.SUBTRACT)
        return sketch

The thickness
-------------

`thickness` is required and must be positive; a node without one fails as
soon as it is constructed, naming itself. It can be a class attribute, as
above, or a constructor argument, in which case one class covers a panel
in two stocks:

.. code-block:: python

    class Panel(Build123dSheetNode):

        def __init__(self, thickness, **kwargs):
            super().__init__(thickness=thickness, **kwargs)

        def profile(self):
            return Rectangle(120, 80)

    thin = Panel(3)
    thick = Panel(6)

Passed as a constructor argument the thickness reaches the node's
artifact key like any other parameter, so those two are two parts with
two sets of artifacts, and neither serves the other's.

Because the thickness is a declared number rather than something buried
in the geometry, the profile can be derived from it — a t-slot that
receives a tab of the same stock is `thickness` wide plus a fit
clearance, written once.

The cut file
------------

Every sheet part writes a **DXF** of its profile beside its `.stl` and
`.brep`, under the same name, whenever a build produces them. It is an
artifact like the others: regenerated when it is stale, left alone when
it is current, and its absence alone is enough to make the build rebuild
the part.

The DXF is *nominal*: the authored profile at model scale, in
millimeters. Circles and arcs are written as arc entities at their
modelled radius rather than tessellated into polylines, so a hole reaches
the cutter as a hole and not as a polygon that would cut tight.

Deliberately not covered yet:

* **Kerf compensation.** The DXF is the nominal profile; the width a
  particular machine burns away on a particular material is not applied.
  The persisted `.brep` keeps the exact profile, so an offsetting
  exporter remains possible.
* **Importing a profile** from SVG or DXF. Profiles are authored in
  build123d.
* **Engraving and marking**, material and process metadata, and nesting
  several parts onto one sheet.

**NOTE**: a `Build123dSheetNode` is not a `Build123dNode` — its
extension point is `profile()`, not `render()` — but it is exact in the
same way, drives the same kernel, and needs no OpenScad. A fusion may
take a sheet part and a CadQuery or build123d part as children and fuse
them exactly.

OpenScadNode
============

The same model can also be obtained using an **OpenScadNode**, which is a small
python wrapper around an OpenScad module.

.. code-block:: python

    from solid_node.node import OpenScadNode

    class DemoProject(OpenScadNode):

        scad_source = 'demo.scad'

Create a file `myproject/demo.scad` with a module to create the model:

.. code-block:: openscad

    module demo() {
      difference() {
        translate([-25, -25, 0]) {
          cube([50, 50, 50]);
        }
        cylinder(r=10, h=100);
      }
    }

And the same model again, driven by the OpenScad module above:

.. solid-node:: _exports/demo_openscad
   :height: 360px

By default the module is expected to have the same name as the file
(`demo.scad` → `module demo()`); if it doesn't, set the `module_name`
property. Arguments passed to the node's constructor are forwarded to the
OpenScad module, so one `.scad` module can back several parametrized
nodes:

.. code-block:: python

    class Demo(OpenScadNode):

        scad_source = 'shapes.scad'
        module_name = 'box_with_hole'

    demo = Demo(50, hole_radius=10)


JScadNode
=========

Finally, the model can also be obtained using a **JScadNode**, which similarly
to OpenScadNode, it's a python wrapper around a JScad function.

You need the **jscad** CLI tool installed in `$PATH`, and its node dependencies
installed in the directory you run `solid` from.

.. code-block:: python

    from solid_node.node import JScadNode

    class DemoProject(JScadNode):

        jscad_source = 'demo.js'

Create a file `myproject/demo.js` with a module to create the model:

.. code-block:: javascript

    const { square, circle } = require('@jscad/modeling').primitives
    const { subtract } = require('@jscad/modeling').booleans
    const { extrudeLinear  } = require('@jscad/modeling').extrusions

    function main() {
      let outerSquare = square({size: 50 });
      let innerCircle = circle({radius: 10 });

      let shape = subtract(outerSquare, innerCircle);
      return extrudeLinear({ height: 50 }, shape);
    }

    module.exports = { main }

And the same model once more, rendered by JScad:

.. solid-node:: _exports/demo_jscad
   :height: 360px

.. _fn-property:

Model resolution: the fn property
=================================

Internally, every part becomes an STL file, and STLs are made of
triangles: circles and holes are approximated by polygons. In
OpenScad-derived nodes — `Solid2Node` and `OpenScadNode` — the number of
segments in that approximation is controlled by OpenScad's `$fn`
variable, and the default is coarse: a small hole can come out as a
hexagon.

Set the `fn` property on the node to raise the resolution:

.. code-block:: python

    class Pointer(Solid2Node):

        fn = 256

CadQuery is not affected — it exports STL files with high precision on
its own.

This is mostly invisible while modeling, but it matters for fits: a
hexagonal "hole" is tighter than the circle it approximates. It comes
back in :doc:`Test-driven CAD <testing>`, where a pin fails to run free
in a low-resolution hole.

Colors
======

Any node can set a `color`, as a hex RGB string, which is used by the
viewer and carried into exports:

.. code-block:: python

    class Pointer(Solid2Node):

        color = '#cc4444'
