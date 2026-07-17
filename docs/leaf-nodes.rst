
.. _leaf-nodes:

==============
Modeling parts
==============

Make sure you have completed the :doc:`Quickstart <quickstart>`.
At this point, you should be able to view your project in the viewer
- either Openscad or the web viewer - and have a source code to edit.

In Solid Node, a project is organized in a tree structure, with leaf
nodes and internal nodes. **Leaf nodes** use underlying modelling
libraries, namely **SolidPython**, **CadQuery**, **OpenScad** and
**JScad**, to generate solid models — each leaf node is one part.
**Internal nodes** combine children nodes into assemblies and fusions,
covered in :doc:`Combining parts <assemblies>`.

Each node implements the `render()` method. Leaf nodes return an object
of the underlying library.

There are four types of LeafNodes, each supporting one underlying
technology to create solids:

* **Solid2Node** Uses Solid Python 2, which is a python wrapper around OpenScad
* **CadQueryNode** Uses CadQuery, a pure python modeler based on OCCT
* **OpenScadNode** A wrapper around one OpenScad module
* **JScadNode** A wrapper around one JScad module

The :doc:`Quickstart <quickstart>` starts with a Solid2Node example showing
a box with a hole. Below are the codes for the same model in each modelling
technology.

Solid2Node
==========

The starting structure created by `solid new` implements a **Solid2Node**
node, which uses **solidpython2** to create models. Open `root/__init__.py`:

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

OpenScadNode
============

The same model can also be obtained using an **OpenScadNode**, which is a small
python wrapper around an OpenScad module.

.. code-block:: python

    from solid_node.node import OpenScadNode

    class DemoProject(OpenScadNode):

        scad_source = 'demo.scad'

Create a file `root/demo.scad` with a module to create the model:

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

Create a file `root/demo.js` with a module to create the model:

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
